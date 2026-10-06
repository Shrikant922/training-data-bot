"""
Performance Benchmarks: Training Data Bot
Measures speed of each component and reports results.
Run: python tests/performance/benchmark.py
"""
import sys
import os
import time
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.chdir(Path(__file__).parent.parent.parent)

import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from tests.fixtures.sample_content import SAMPLE_TEXT, SAMPLE_CSV, SAMPLE_JSON

from training_data_bot.preprocessing.preprocessor import TextPreprocessor
from training_data_bot.preprocessing.chunker import TextChunker
from training_data_bot.core.models import Document, DocumentType, TrainingExample, Dataset, TaskType
from training_data_bot.evaluation.evaluator import QualityEvaluator
from training_data_bot.storage.exporter import DatasetExporter
from uuid import uuid4
import tempfile


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_document(content: str, n: int = 1) -> Document:
    return Document(
        title=f"Benchmark Doc {n}",
        content=content * n,  # scale content
        source="benchmark.txt",
        doc_type=DocumentType.TXT,
        word_count=len((content * n).split()),
        char_count=len(content * n)
    )

def make_examples(n: int) -> list:
    doc_id = uuid4()
    return [
        TrainingExample(
            input_text=f"What is concept {i} in machine learning?",
            output_text=f"Concept {i} relates to the application of statistical methods to learn from data.",
            task_type=TaskType.QA_GENERATION,
            source_document_id=doc_id
        )
        for i in range(n)
    ]

class Timer:
    def __init__(self, label: str):
        self.label = label

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *_):
        self.elapsed = (time.perf_counter() - self.start) * 1000  # ms
        status = "OK" if self.elapsed < self.threshold else "SLOW"
        print(f"  [{status}] {self.label:<50} {self.elapsed:>8.1f} ms  (target: <{self.threshold}ms)")

    def with_threshold(self, ms: float):
        self.threshold = ms
        return self


# ─────────────────────────────────────────────────────────────────────────────
# Benchmarks
# ─────────────────────────────────────────────────────────────────────────────

async def run_benchmarks():
    print("=" * 75)
    print("  TRAINING DATA BOT - PERFORMANCE BENCHMARK")
    print("=" * 75)

    results = {}

    # 1. TextPreprocessor
    print("\n[1] TextPreprocessor")
    preprocessor = TextPreprocessor()
    long_text = SAMPLE_TEXT * 5  # ~5x amplify

    with Timer("preprocess() - single doc (~5KB)").with_threshold(50) as t:
        preprocessor.preprocess(long_text)
    results["preprocess_single"] = t.elapsed

    with Timer("preprocess() x100 docs sequentially").with_threshold(500) as t:
        for _ in range(100):
            preprocessor.preprocess(SAMPLE_TEXT)
    results["preprocess_100"] = t.elapsed

    with Timer("clean_for_training() - single doc").with_threshold(50) as t:
        preprocessor.clean_for_training(long_text)
    results["clean_for_training"] = t.elapsed

    # 2. TextChunker
    print("\n[2] TextChunker")
    chunker = TextChunker(chunk_size=500, chunk_overlap=100)
    big_doc = make_document(SAMPLE_TEXT, n=5)  # ~5KB doc

    with Timer("chunk_document() - 5KB doc (default settings)").with_threshold(100) as t:
        chunks = chunker.chunk_document(big_doc)
    results["chunk_5kb"] = t.elapsed
    print(f"         --> Produced {len(chunks)} chunks from {big_doc.char_count:,} chars")

    very_big_doc = make_document(SAMPLE_TEXT, n=50)  # ~50KB doc
    with Timer("chunk_document() - 50KB doc").with_threshold(500) as t:
        big_chunks = chunker.chunk_document(very_big_doc)
    results["chunk_50kb"] = t.elapsed
    print(f"         --> Produced {len(big_chunks)} chunks from {very_big_doc.char_count:,} chars")

    # Chunker throughput
    with Timer("chunk_document() x50 docs sequentially").with_threshold(2000) as t:
        for _ in range(50):
            chunker.chunk_document(big_doc)
    results["chunk_50_docs"] = t.elapsed

    # 3. QualityEvaluator
    print("\n[3] QualityEvaluator")
    evaluator = QualityEvaluator()
    from training_data_bot.core.models import TrainingExample

    example = TrainingExample(
        input_text="What is machine learning?",
        output_text="Machine learning is a method of data analysis that automates analytical model building.",
        task_type=TaskType.QA_GENERATION,
        source_document_id=uuid4()
    )

    with Timer("evaluate_example() - single example").with_threshold(50) as t:
        await evaluator.evaluate_example(example)
    results["evaluate_single"] = t.elapsed

    examples_10 = make_examples(10)
    ds_10 = Dataset(name="bench", description="bench", examples=examples_10, total_examples=10)

    with Timer("evaluate_dataset() - 10 examples").with_threshold(500) as t:
        await evaluator.evaluate_dataset(ds_10)
    results["evaluate_10"] = t.elapsed

    examples_100 = make_examples(100)
    ds_100 = Dataset(name="bench", description="bench", examples=examples_100, total_examples=100)

    with Timer("filter_dataset() - 100 examples").with_threshold(2000) as t:
        filtered = await evaluator.filter_dataset(ds_100)
    results["filter_100"] = t.elapsed
    print(f"         --> {len(filtered.examples)}/100 examples passed quality filter")

    # 4. DatasetExporter
    print("\n[4] DatasetExporter")
    exporter = DatasetExporter(include_metadata=False)

    with tempfile.TemporaryDirectory() as tmpdir:
        examples_1000 = make_examples(1000)
        ds_1000 = Dataset(name="bench", description="bench", examples=examples_1000, total_examples=1000)

        out_jsonl = Path(tmpdir) / "bench.jsonl"
        with Timer("export_dataset() JSONL - 1000 examples").with_threshold(1000) as t:
            await exporter.export_dataset(ds_1000, out_jsonl, format="jsonl")
        results["export_1000_jsonl"] = t.elapsed
        size_kb = out_jsonl.stat().st_size / 1024
        print(f"         --> File size: {size_kb:.1f} KB")

        out_csv = Path(tmpdir) / "bench.csv"
        with Timer("export_dataset() CSV - 1000 examples").with_threshold(1000) as t:
            await exporter.export_dataset(ds_1000, out_csv, format="csv")
        results["export_1000_csv"] = t.elapsed

        out_json = Path(tmpdir) / "bench.json"
        with Timer("export_dataset() JSON - 1000 examples").with_threshold(1000) as t:
            await exporter.export_dataset(ds_1000, out_json, format="json")
        results["export_1000_json"] = t.elapsed

        out_split = Path(tmpdir) / "splits"
        with Timer("export_split_dataset() - 1000 examples").with_threshold(2000) as t:
            await exporter.export_split_dataset(ds_1000, out_split, format="jsonl")
        results["export_split_1000"] = t.elapsed

    # 5. Document Loading (local files only — no network)
    print("\n[5] Document Loading")
    from training_data_bot.sources.document import DocumentLoader

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create 10 text files
        files = []
        for i in range(10):
            p = Path(tmpdir) / f"doc_{i}.txt"
            p.write_text(SAMPLE_TEXT * 2, encoding="utf-8")
            files.append(p)

        loader = DocumentLoader()

        # Sequential
        with Timer("Load 1 TXT file").with_threshold(100) as t:
            await loader.load_single(files[0])
        results["load_single_txt"] = t.elapsed

        with Timer("Load 10 TXT files sequentially").with_threshold(500) as t:
            for f in files:
                await loader.load_single(f)
        results["load_10_sequential"] = t.elapsed

        # Parallel
        with Timer("Load 10 TXT files in parallel (max_workers=5)").with_threshold(200) as t:
            docs = await loader.load_multiple(files, max_workers=5)
        results["load_10_parallel"] = t.elapsed
        print(f"         --> Loaded {len(docs)} documents")

    # ─────────────────────────────────────────────────────────────────────────
    # Summary
    # ─────────────────────────────────────────────────────────────────────────
    print("\n" + "=" * 75)
    print("  SUMMARY")
    print("=" * 75)
    parallel_speedup = results["load_10_sequential"] / max(results["load_10_parallel"], 0.1)
    print(f"\n  Parallel load speedup:          {parallel_speedup:.1f}x (vs sequential)")
    print(f"  Preprocess throughput:          {100 / results['preprocess_100'] * 1000:.0f} docs/sec")
    print(f"  Chunk throughput:               {50 / results['chunk_50_docs'] * 1000:.0f} docs/sec")
    print(f"  Quality eval throughput:        {10 / results['evaluate_10'] * 1000:.0f} examples/sec")
    print(f"  JSONL export throughput:        {1000 / results['export_1000_jsonl'] * 1000:.0f} examples/sec")

    slow = [k for k, v in results.items() if v > {
        "preprocess_single": 50, "chunk_5kb": 100,
        "evaluate_single": 50, "export_1000_jsonl": 1000,
        "load_single_txt": 100,
    }.get(k, float("inf"))]

    if slow:
        print(f"\n  [WARN] Slow operations found: {slow}")
    else:
        print("\n  All benchmarks within target thresholds.")

    print("=" * 75)
    return results


if __name__ == "__main__":
    asyncio.run(run_benchmarks())
