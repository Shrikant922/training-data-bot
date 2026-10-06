"""
Phase 1: Smoke Test - Verify all imports and instantiation work.
Run: python tests/smoke_test.py
"""
import sys
import os
import asyncio
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Force working directory to project root so .env is found
os.chdir(Path(__file__).parent.parent)

# Force UTF-8 output
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

PASS = "[PASS]"
FAIL = "[FAIL]"
WARN = "[WARN]"

results = []

def check(name, fn):
    try:
        result = fn()
        print(f"  {PASS}  {name}")
        results.append(("PASS", name))
        return result
    except Exception as e:
        print(f"  {FAIL}  {name}")
        print(f"          Error: {e}")
        results.append(("FAIL", name, str(e)))
        return None

print("=" * 60)
print("  TRAINING DATA BOT — SMOKE TEST")
print("=" * 60)

# -------------------------------------------------------
print("\n[1] Core imports")
check("pydantic_settings import", lambda: __import__("pydantic_settings"))
check("training_data_bot package import", lambda: __import__("training_data_bot"))
check("TrainingDataBot class import", lambda: __import__("training_data_bot", fromlist=["TrainingDataBot"]).TrainingDataBot)

# -------------------------------------------------------
print("\n[2] Core submodules")
check("core.models", lambda: __import__("training_data_bot.core.models", fromlist=["Document"]).Document)
check("core.config", lambda: __import__("training_data_bot.core.config", fromlist=["settings"]).settings)
check("core.logging", lambda: __import__("training_data_bot.core.logging", fromlist=["get_logger"]).get_logger)
check("core.exceptions", lambda: __import__("training_data_bot.core.exceptions", fromlist=["TrainingDataBotError"]).TrainingDataBotError)

# -------------------------------------------------------
print("\n[3] Settings load from .env")
from training_data_bot.core.config import settings
check("openai_api_key is set", lambda: settings.openai_api_key if settings.openai_api_key else (_ for _ in ()).throw(ValueError("API key missing")))
check("chunk_size is integer > 0", lambda: settings.chunk_size if settings.chunk_size > 0 else (_ for _ in ()).throw(ValueError()))
check("quality_threshold is 0.0-1.0", lambda: settings.quality_threshold if 0 <= settings.quality_threshold <= 1 else (_ for _ in ()).throw(ValueError()))

# -------------------------------------------------------
print("\n[4] Component instantiation (no API key needed)")
check("TextPreprocessor()", lambda: __import__("training_data_bot.preprocessing.preprocessor", fromlist=["TextPreprocessor"]).TextPreprocessor())
check("TextChunker()", lambda: __import__("training_data_bot.preprocessing.chunker", fromlist=["TextChunker"]).TextChunker())
check("QualityEvaluator()", lambda: __import__("training_data_bot.evaluation.evaluator", fromlist=["QualityEvaluator"]).QualityEvaluator())
check("DatasetExporter()", lambda: __import__("training_data_bot.storage.exporter", fromlist=["DatasetExporter"]).DatasetExporter())
check("DatabaseManager()", lambda: __import__("training_data_bot.storage.database", fromlist=["DatabaseManager"]).DatabaseManager())
check("DecodoClient()", lambda: __import__("training_data_bot.decodo.client", fromlist=["DecodoClient"]).DecodoClient())
check("PDFLoader()", lambda: __import__("training_data_bot.sources.pdf", fromlist=["PDFLoader"]).PDFLoader())
check("WebLoader()", lambda: __import__("training_data_bot.sources.web", fromlist=["WebLoader"]).WebLoader())
check("DocumentLoader()", lambda: __import__("training_data_bot.sources.document", fromlist=["DocumentLoader"]).DocumentLoader())
check("UnifiedLoader()", lambda: __import__("training_data_bot.sources.unified", fromlist=["UnifiedLoader"]).UnifiedLoader())

# -------------------------------------------------------
print("\n[5] AIClient instantiation (lazy — should NOT need key at init)")
check("AIClient() constructs without crashing",
    lambda: __import__("training_data_bot.ai.client", fromlist=["AIClient"]).AIClient())

# -------------------------------------------------------
print("\n[6] TrainingDataBot full construction")
check("TrainingDataBot() constructs without crashing",
    lambda: __import__("training_data_bot", fromlist=["TrainingDataBot"]).TrainingDataBot())

# -------------------------------------------------------
print("\n[7] Data models")
from training_data_bot.core.models import (
    Document, TextChunk, TrainingExample, Dataset,
    TaskTemplate, TaskResult, QualityReport, ProcessingJob,
    DocumentType, TaskType, QualityMetric, ProcessingStatus, ExportFormat
)
from uuid import uuid4
from datetime import datetime

def make_document():
    return Document(title="Test", content="Hello world", source="test.txt",
                    doc_type=DocumentType.TXT, word_count=2, char_count=11)

check("Document model creates", make_document)
check("DocumentType enum has PDF", lambda: DocumentType.PDF)
check("TaskType enum has QA_GENERATION", lambda: TaskType.QA_GENERATION)
check("Dataset model creates with empty examples", lambda: Dataset(name="test", description="test"))

# -------------------------------------------------------
print("\n[8] OpenAI client compatibility check")
def check_openai_client():
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key="test-key")
    return client

check("openai.AsyncOpenAI() can be constructed", check_openai_client)

# -------------------------------------------------------
print("\n" + "=" * 60)
passed = sum(1 for r in results if r[0] == "PASS")
failed = sum(1 for r in results if r[0] == "FAIL")
print(f"  RESULTS: {passed} passed, {failed} failed out of {len(results)} checks")
print("=" * 60)

if failed > 0:
    print("\n  FAILED CHECKS:")
    for r in results:
        if r[0] == "FAIL":
            print(f"    - {r[1]}: {r[2]}")
    sys.exit(1)
else:
    print("\n  ALL SMOKE TESTS PASSED ✅")
    sys.exit(0)
