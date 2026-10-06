"""
FastAPI Server for Training Data Bot.
Provides high-throughput API endpoints for document ingestion, real-time SSE generation,
SQLite cache telemetry, and dataset packaging.
"""

import asyncio
import io
import json
import os
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from training_data_bot.bot import TrainingDataBot
from training_data_bot.core.config import settings
from training_data_bot.core.models import Dataset, Document, TaskType, TrainingExample

# Initialize FastAPI App
app = FastAPI(
    title="Training Data Bot API",
    description="High-throughput pipeline for LLM fine-tuning datasets",
    version="0.1.0"
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Project paths
BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
STATIC_DIR.mkdir(parents=True, exist_ok=True)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Initialize Training Data Bot orchestrator
bot = TrainingDataBot()

# In-memory session state
state: Dict[str, Any] = {
    "active_document": None,
    "active_chunks": [],
    "active_dataset": None,
    "latest_report": None
}


# =============================================================================
# MODELS
# =============================================================================

class GenerateRequest(BaseModel):
    task_type: str = "qa"  # qa, summary, classification
    concurrency: int = 15
    quality_threshold: float = 0.70
    custom_categories: Optional[List[str]] = None
    summary_style: Optional[str] = "concise"


class ExportRequest(BaseModel):
    format: str = "jsonl"  # jsonl, csv, json
    split: bool = True
    train_ratio: float = 0.8
    val_ratio: float = 0.1
    test_ratio: float = 0.1


# =============================================================================
# ROOT & STATUS ENDPOINTS
# =============================================================================

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    """Serve the main web UI."""
    index_file = STATIC_DIR / "landing.html"
    if not index_file.exists():
        raise HTTPException(status_code=404, detail="landing.html not found")
    return HTMLResponse(content=index_file.read_text(encoding="utf-8"))

@app.get("/app", response_class=HTMLResponse)
async def serve_app():
    """Serve the workspace UI."""
    app_file = STATIC_DIR / "app.html"
    if not app_file.exists():
        raise HTTPException(status_code=404, detail="app.html not found")
    return HTMLResponse(content=app_file.read_text(encoding="utf-8"))


@app.get("/api/status")
async def get_status():
    """Get system health and engine status."""
    cache_stats = bot.ai_client.cache.get_stats() if hasattr(bot.ai_client, "cache") and bot.ai_client.cache else {}
    return {
        "status": "online",
        "engine": "ready",
        "concurrency_default": settings.max_concurrent_requests,
        "cache_stats": cache_stats,
        "has_document": state["active_document"] is not None,
        "chunks_count": len(state["active_chunks"]),
        "has_dataset": state["active_dataset"] is not None,
        "dataset_examples": len(state["active_dataset"].examples) if state["active_dataset"] else 0
    }


@app.get("/api/cache-stats")
async def get_cache_stats():
    """Retrieve SQLite response cache statistics."""
    if hasattr(bot.ai_client, "cache") and bot.ai_client.cache:
        stats = bot.ai_client.cache.get_stats()
    else:
        stats = {"total_entries": 0, "total_hits": 0, "total_misses": 0, "hit_ratio": 0.0}
    return stats


# =============================================================================
# DOCUMENT INGESTION
# =============================================================================

@app.post("/api/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Ingest a document (PDF, TXT, MD, JSON, CSV), clean it, and chunk it.
    """
    try:
        suffix = Path(file.filename).suffix or ".txt"
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            content = await file.read()
            tmp.write(content)
            tmp_path = Path(tmp.name)

        # Load through UnifiedLoader
        docs = await bot.load_documents([tmp_path])
        if not docs:
            raise HTTPException(status_code=400, detail="Failed to parse document content")

        doc = docs[0]
        # Preserve original user filename
        doc.source = file.filename

        # Preprocess and chunk
        cleaned = bot.preprocessor.clean_for_training(doc.content)
        doc.content = cleaned
        chunks = bot.chunker.chunk_document(doc)

        # Update session state
        state["active_document"] = doc
        state["active_chunks"] = chunks
        state["active_dataset"] = None

        # Clean up temp file
        if tmp_path.exists():
            tmp_path.unlink()

        return {
            "success": True,
            "filename": file.filename,
            "size_bytes": len(content),
            "size_kb": round(len(content) / 1024, 2),
            "chunks_count": len(chunks),
            "total_tokens": sum(c.token_count for c in chunks),
            "preview_chunks": [
                {
                    "id": str(c.id)[:8],
                    "index": c.chunk_index,
                    "tokens": c.token_count,
                    "preview": c.content[:160] + ("..." if len(c.content) > 160 else "")
                }
                for c in chunks[:5]
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/load-sample")
async def load_sample_document(sample_name: str = Query(..., description="sample ID or name")):
    """
    Load a pre-configured sample document for instant testing.
    """
    samples = {
        "research": {
            "title": "Transformer_Research.pdf",
            "content": """The Transformer model relies entirely on self-attention mechanisms to compute representations of its input and output without using sequence-aligned RNNs or convolution. In the self-attention layer, the queries and keys of dimension d_k, and values of dimension d_v are packed together into matrices Q, K, and V. The matrix of outputs is computed as Attention(Q, K, V) = softmax(Q K^T / sqrt(d_k)) V. Scaling by sqrt(d_k) prevents vanishing gradients in softmax during deep matrix multiplication. Multi-head attention allows the model to jointly attend to information from different representation subspaces at different positions. Sentence-boundary snapping in chunking pipelines ensures that these attention concepts are not fragmented across partial sentences."""
        },
        "support": {
            "title": "Customer_Support_Transcripts.txt",
            "content": """Customer: Hello, my API key is returning a 429 Too Many Requests rate limit error when sending concurrent batch requests.
Agent: Hi! Rate limits depend on your organization's tier. To avoid 429 errors, implement an exponential backoff retry policy or increase your rate limit tier in the dashboard.
Customer: Can I also cache the responses locally so duplicate chunk prompts don't hit the API?
Agent: Absolutely! Enabling an SQLite-backed response cache keyed on SHA-256 hashes of chunk content allows repeat runs to return in under 0.07 seconds at zero token cost."""
        },
        "faq": {
            "title": "Medical_Clinical_FAQ.json",
            "content": """Question: What safety protocols are mandated for clinical software delivery?
Answer: Healthcare software delivery requires strict compliance approvals, end-to-end audit trails, patient data anonymization, and HIPAA-compliant data encryption both in transit and at rest.
Question: How does synthetic training data generation protect patient privacy?
Answer: By transforming clinical guidelines into anonymized Q&A pairs without extracting Protected Health Information (PHI), organizations can safely fine-tune domain-specific models."""
        }
    }

    sample_data = samples.get(sample_name.lower())
    if not sample_data:
        raise HTTPException(status_code=404, detail="Sample not found")

    content_str = sample_data["content"]
    ext = Path(sample_data["title"]).suffix.lower().replace(".", "")
    try:
        from training_data_bot.core.models import DocumentType
        d_type = DocumentType(ext)
    except Exception:
        d_type = DocumentType.TXT

    doc = Document(
        title=sample_data["title"],
        content=content_str,
        source=sample_data["title"],
        doc_type=d_type,
        word_count=len(content_str.split()),
        char_count=len(content_str)
    )
    cleaned = bot.preprocessor.clean_for_training(doc.content)
    doc.content = cleaned
    chunks = bot.chunker.chunk_document(doc)

    state["active_document"] = doc
    state["active_chunks"] = chunks
    state["active_dataset"] = None

    return {
        "success": True,
        "filename": sample_data["title"],
        "size_bytes": len(sample_data["content"].encode("utf-8")),
        "size_kb": round(len(sample_data["content"].encode("utf-8")) / 1024, 2),
        "chunks_count": len(chunks),
        "total_tokens": sum(c.token_count for c in chunks),
        "preview_chunks": [
            {
                "id": str(c.id)[:8],
                "index": c.chunk_index,
                "tokens": c.token_count,
                "preview": c.content[:160] + ("..." if len(c.content) > 160 else "")
            }
            for c in chunks
        ]
    }


# =============================================================================
# GENERATION PIPELINE (SSE STREAMING)
# =============================================================================

@app.post("/api/generate")
async def generate_dataset(req: GenerateRequest):
    """
    Trigger batch fine-tuning dataset generation with Server-Sent Events (SSE).
    Streams real-time progress, chunk completions, token counts, and quality metrics.
    """
    if not state["active_chunks"]:
        # If no document uploaded yet, load default research sample
        await load_sample_document("research")

    # Map task type
    task_map = {
        "qa": TaskType.QA_GENERATION,
        "summary": TaskType.SUMMARIZATION,
        "classify": TaskType.CLASSIFICATION,
        "classification": TaskType.CLASSIFICATION
    }
    task_type = task_map.get(req.task_type.lower(), TaskType.QA_GENERATION)

    task_config: Dict[str, Any] = {
        "max_concurrent": req.concurrency,
    }
    if req.custom_categories:
        task_config["categories"] = req.custom_categories
    if req.summary_style:
        task_config["style"] = req.summary_style

    event_queue: asyncio.Queue = asyncio.Queue()

    # Progress callback from bot.py
    def on_progress(completed: int, total: int, latest_result: Any):
        # Extract example fields
        item_data = {}
        if isinstance(latest_result, TrainingExample):
            item_data = {
                "id": str(latest_result.id)[:8],
                "input": latest_result.prompt or latest_result.input_text or "",
                "output": latest_result.completion or latest_result.output_text or "",
                "tokens": latest_result.token_count or (len(str(latest_result.completion)) // 4),
                "quality_score": round(latest_result.quality_score or 0.95, 2)
            }
        event_queue.put_nowait({
            "event": "progress",
            "completed": completed,
            "total": total,
            "example": item_data
        })

    async def run_pipeline():
        try:
            # Process chunks through bot orchestrator
            doc = state["active_document"]
            dataset = await bot.process_documents(
                documents=[doc],
                task_type=task_type,
                task_config=task_config,
                filter_quality=True,
                on_progress=on_progress
            )
            # Evaluate overall dataset
            report = await bot.evaluate_dataset(dataset)
            state["active_dataset"] = dataset
            state["latest_report"] = report

            # Send complete event
            await event_queue.put({
                "event": "complete",
                "total_generated": len(dataset.examples),
                "quality_score": round(report["overall_score"], 2),
                "metrics": report.get("metric_scores", {}),
                "dataset_id": str(dataset.id)
            })
        except Exception as e:
            await event_queue.put({
                "event": "error",
                "message": str(e)
            })
        finally:
            await event_queue.put(None)  # Sentinel to end stream

    # Launch background generation task
    asyncio.create_task(run_pipeline())

    # Stream generator
    async def sse_generator():
        while True:
            event = await event_queue.get()
            if event is None:
                break
            event_type = event.get("event", "message")
            yield f"event: {event_type}\ndata: {json.dumps(event)}\n\n"

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )


# =============================================================================
# DATASET EXPORT
# =============================================================================

@app.post("/api/export")
async def export_dataset_endpoint(req: ExportRequest):
    """
    Export current dataset as .jsonl, .csv, or a partitioned .zip package.
    """
    dataset = state["active_dataset"]
    if not dataset or not dataset.examples:
        raise HTTPException(status_code=400, detail="No dataset available. Please run generation first.")

    temp_dir = Path(tempfile.mkdtemp())
    try:
        fmt = req.format.lower()
        if fmt not in ["jsonl", "csv", "json"]:
            fmt = "jsonl"

        if not req.split:
            # Single file export
            out_file = temp_dir / f"training_dataset.{fmt}"
            await bot.export_dataset(dataset, out_file, format=fmt, split=False)
            return FileResponse(
                path=out_file,
                filename=f"training_dataset.{fmt}",
                media_type="application/octet-stream"
            )
        else:
            # Partitioned Train/Val/Test Split Package
            split_files = await bot.export_dataset(
                dataset,
                temp_dir,
                format=fmt,
                split=True
            )
            # Package into zip
            zip_path = temp_dir / "training_vault_package.zip"
            with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zip_f:
                if isinstance(split_files, dict):
                    for name, p in split_files.items():
                        if Path(p).exists():
                            zip_f.write(p, arcname=f"{name}.{fmt}")
                # Also include metadata README
                readme_content = f"""Training Data Bot - Dataset Export Vault
============================================
Total Examples: {len(dataset.examples)}
Export Format:  {fmt.upper()}
Split Strategy: Train (80%) / Val (10%) / Test (10%)
Quality Score:  {state['latest_report']['overall_score'] if state.get('latest_report') else 1.0}
Generated By:   Training Data Bot v0.1.0
============================================
"""
                zip_f.writestr("DATASET_INFO.txt", readme_content)

            return FileResponse(
                path=zip_path,
                filename="training_vault_package.zip",
                media_type="application/zip"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
