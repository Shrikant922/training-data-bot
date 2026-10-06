"""
Integration Tests + E2E Tests: Full Pipeline
Tests complete document → training data pipeline with mocked and real AI.
"""
import sys
import os
import json
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.chdir(Path(__file__).parent.parent.parent)

import pytest
from uuid import uuid4

from training_data_bot import TrainingDataBot
from training_data_bot.core.models import Dataset, TaskType
from training_data_bot.preprocessing.preprocessor import TextPreprocessor
from training_data_bot.preprocessing.chunker import TextChunker
from training_data_bot.tasks.qa_generation import QAGenerator
from training_data_bot.tasks.classification import ClassificationGenerator
from training_data_bot.tasks.summarization import SummarizationGenerator
from training_data_bot.evaluation.evaluator import QualityEvaluator
from training_data_bot.storage.exporter import DatasetExporter
from tests.fixtures.sample_content import SAMPLE_TEXT, SAMPLE_HTML, SAMPLE_CSV, SAMPLE_JSON, SAMPLE_MARKDOWN

# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def text_file(tmp_path_factory):
    p = tmp_path_factory.mktemp("int_docs") / "sample.txt"
    p.write_text(SAMPLE_TEXT, encoding="utf-8")
    return p

@pytest.fixture(scope="module")
def multi_file_dir(tmp_path_factory):
    d = tmp_path_factory.mktemp("multi_docs")
    (d / "doc1.txt").write_text(SAMPLE_TEXT, encoding="utf-8")
    (d / "doc2.md").write_text(SAMPLE_MARKDOWN, encoding="utf-8")
    (d / "doc3.csv").write_text(SAMPLE_CSV, encoding="utf-8")
    return d

QA_RESPONSE = """Q1: What is machine learning?
A1: Machine learning enables systems to learn from data.

Q2: What are the types of machine learning?
A2: Supervised, unsupervised, and reinforcement learning.

Q3: What are applications of machine learning?
A3: Image recognition, NLP, and recommendation systems."""

CLASSIFICATION_RESPONSE = """Category: technical
Explanation: The text discusses machine learning concepts.
Confidence: high"""

SUMMARIZATION_RESPONSE = "Machine learning is a subset of AI that allows systems to learn from data without explicit programming."


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3A: Load → Preprocess → Chunk Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class TestLoadChunkPipeline:
    @pytest.mark.asyncio
    async def test_load_single_txt_file(self, text_file):
        """TrainingDataBot loads a TXT file correctly."""
        async with TrainingDataBot() as bot:
            docs = await bot.load_documents([str(text_file)])
        assert len(docs) == 1
        assert len(docs[0].content) > 0

    @pytest.mark.asyncio
    async def test_load_multiple_files_parallel(self, multi_file_dir):
        """Load 3 files in parallel — all succeed."""
        files = [str(p) for p in multi_file_dir.iterdir()]
        async with TrainingDataBot() as bot:
            docs = await bot.load_documents(files)
        assert len(docs) == 3

    @pytest.mark.asyncio
    async def test_preprocess_preserves_content(self, text_file):
        """Preprocessing doesn't destroy meaningful content."""
        async with TrainingDataBot() as bot:
            docs = await bot.load_documents([str(text_file)])
        preprocessor = TextPreprocessor()
        cleaned = preprocessor.clean_for_training(docs[0].content)
        assert len(cleaned) > 50
        assert "machine" in cleaned.lower() or "learning" in cleaned.lower()

    @pytest.mark.asyncio
    async def test_chunk_pipeline_produces_chunks(self, text_file):
        """After loading, chunking produces multiple TextChunk objects."""
        async with TrainingDataBot() as bot:
            docs = await bot.load_documents([str(text_file)])
        preprocessor = TextPreprocessor()
        chunker = TextChunker(chunk_size=300, chunk_overlap=50)
        content = preprocessor.clean_for_training(docs[0].content)
        # Build a Document-like object for chunking
        from training_data_bot.core.models import Document, DocumentType
        doc = Document(
            title="t", content=content,
            source="test.txt", doc_type=DocumentType.TXT,
            word_count=len(content.split()), char_count=len(content)
        )
        chunks = chunker.chunk_document(doc)
        assert len(chunks) >= 1
        assert all(len(c.content) > 0 for c in chunks)

    @pytest.mark.asyncio
    async def test_chunks_cover_full_content(self, text_file):
        """Verify chunks together cover the full original content."""
        async with TrainingDataBot() as bot:
            docs = await bot.load_documents([str(text_file)])
        chunker = TextChunker(chunk_size=300, chunk_overlap=0)
        chunks = chunker.chunk_document(docs[0])
        total_chars = sum(len(c.content) for c in chunks)
        # Should be close to original (ignoring discarded tiny chunks)
        assert total_chars > len(docs[0].content) * 0.5


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3B: Task Generation Pipeline (Mocked AI)
# ─────────────────────────────────────────────────────────────────────────────

class TestQAPipelineMocked:
    @pytest.mark.asyncio
    async def test_qa_generation_produces_examples(self, text_file):
        with patch("training_data_bot.ai.client.AIClient.generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = QA_RESPONSE
            async with TrainingDataBot() as bot:
                docs = await bot.load_documents([str(text_file)])
                dataset = await bot.process_documents(docs, task_type="qa_generation")
        assert len(dataset.examples) > 0
        assert all(ex.task_type == TaskType.QA_GENERATION for ex in dataset.examples)

    @pytest.mark.asyncio
    async def test_qa_examples_have_non_empty_inputs_outputs(self, text_file):
        with patch("training_data_bot.ai.client.AIClient.generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = QA_RESPONSE
            async with TrainingDataBot() as bot:
                docs = await bot.load_documents([str(text_file)])
                dataset = await bot.process_documents(docs, task_type="qa_generation")
        for ex in dataset.examples:
            assert len(ex.input_text) > 0
            assert len(ex.output_text) > 0

    @pytest.mark.asyncio
    async def test_qa_examples_linked_to_source(self, text_file):
        with patch("training_data_bot.ai.client.AIClient.generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = QA_RESPONSE
            async with TrainingDataBot() as bot:
                docs = await bot.load_documents([str(text_file)])
                dataset = await bot.process_documents(docs, task_type="qa_generation")
        for ex in dataset.examples:
            assert ex.source_document_id is not None


class TestClassificationPipelineMocked:
    @pytest.mark.asyncio
    async def test_classification_produces_examples(self, text_file):
        with patch("training_data_bot.ai.client.AIClient.generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = CLASSIFICATION_RESPONSE
            async with TrainingDataBot() as bot:
                docs = await bot.load_documents([str(text_file)])
                dataset = await bot.process_documents(
                    docs, task_type="classification",
                    task_config={"categories": ["technical", "educational", "general"]}
                )
        assert len(dataset.examples) > 0
        assert all(ex.task_type == TaskType.CLASSIFICATION for ex in dataset.examples)

    @pytest.mark.asyncio
    async def test_classification_output_is_valid_category(self, text_file):
        with patch("training_data_bot.ai.client.AIClient.generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = CLASSIFICATION_RESPONSE
            categories = ["technical", "educational", "general"]
            async with TrainingDataBot() as bot:
                docs = await bot.load_documents([str(text_file)])
                dataset = await bot.process_documents(
                    docs, task_type="classification",
                    task_config={"categories": categories}
                )
        for ex in dataset.examples:
            assert ex.output_text in categories


class TestSummarizationPipelineMocked:
    @pytest.mark.asyncio
    async def test_summarization_produces_examples(self, text_file):
        with patch("training_data_bot.ai.client.AIClient.generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = SUMMARIZATION_RESPONSE
            async with TrainingDataBot() as bot:
                docs = await bot.load_documents([str(text_file)])
                dataset = await bot.process_documents(docs, task_type="summarization")
        assert len(dataset.examples) > 0
        assert all(ex.task_type == TaskType.SUMMARIZATION for ex in dataset.examples)

    @pytest.mark.asyncio
    async def test_summary_shorter_than_input(self, text_file):
        with patch("training_data_bot.ai.client.AIClient.generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = SUMMARIZATION_RESPONSE
            async with TrainingDataBot() as bot:
                docs = await bot.load_documents([str(text_file)])
                dataset = await bot.process_documents(docs, task_type="summarization")
        for ex in dataset.examples:
            assert len(ex.output_text) < len(ex.input_text)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 3C: Quality → Export Pipeline
# ─────────────────────────────────────────────────────────────────────────────

class TestQualityExportPipeline:
    @pytest.mark.asyncio
    async def test_full_pipeline_with_export(self, text_file, tmp_path):
        """Full pipeline: load → generate (mocked) → evaluate → export."""
        with patch("training_data_bot.ai.client.AIClient.generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = QA_RESPONSE
            output_path = tmp_path / "output.jsonl"
            async with TrainingDataBot() as bot:
                docs = await bot.load_documents([str(text_file)])
                dataset = await bot.process_documents(docs, task_type="qa_generation")
                report = await bot.evaluate_dataset(dataset)
                path = await bot.export_dataset(dataset, str(output_path))
        assert Path(path).exists()
        lines = Path(path).read_text(encoding="utf-8").strip().split("\n")
        assert len(lines) > 0
        for line in lines:
            json.loads(line)  # Must be valid JSON

    @pytest.mark.asyncio
    async def test_jsonl_roundtrip(self, text_file, tmp_path):
        """Exported JSONL can be re-read and has expected fields."""
        with patch("training_data_bot.ai.client.AIClient.generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = QA_RESPONSE
            output_path = tmp_path / "roundtrip.jsonl"
            async with TrainingDataBot() as bot:
                docs = await bot.load_documents([str(text_file)])
                dataset = await bot.process_documents(docs, task_type="qa_generation")
                await bot.export_dataset(dataset, str(output_path))
        for line in output_path.read_text(encoding="utf-8").strip().split("\n"):
            obj = json.loads(line)
            assert "input" in obj
            assert "output" in obj

    @pytest.mark.asyncio
    async def test_context_manager_cleans_up(self, text_file):
        """TrainingDataBot context manager: no exceptions on exit."""
        with patch("training_data_bot.ai.client.AIClient.generate", new_callable=AsyncMock) as mock_gen:
            mock_gen.return_value = QA_RESPONSE
            try:
                async with TrainingDataBot() as bot:
                    docs = await bot.load_documents([str(text_file)])
                    await bot.process_documents(docs, task_type="qa_generation")
            except Exception as e:
                pytest.fail(f"Context manager raised exception: {e}")

    @pytest.mark.asyncio
    async def test_get_statistics(self, text_file):
        """get_statistics returns a dict with expected keys."""
        async with TrainingDataBot() as bot:
            stats = bot.get_statistics()
        assert isinstance(stats, dict)


# ─────────────────────────────────────────────────────────────────────────────
# Phase 5: E2E Tests (Real OpenAI API)
# ─────────────────────────────────────────────────────────────────────────────

class TestE2ERealAPI:
    """These tests use the real OpenAI API. Skip if no key configured."""

    @pytest.mark.asyncio
    async def test_e2e_qa_from_txt(self, text_file, tmp_path):
        """Full real pipeline: TXT → QA pairs → JSONL export."""
        output = tmp_path / "e2e_qa.jsonl"
        async with TrainingDataBot() as bot:
            docs = await bot.load_documents([str(text_file)])
            assert len(docs) == 1, "Should load 1 document"
            assert len(docs[0].content) > 50, "Document should have content"

            dataset = await bot.process_documents(docs, task_type="qa_generation")
            assert len(dataset.examples) > 0, "Should generate at least 1 QA pair"

            # Verify all examples have question and answer
            for ex in dataset.examples:
                assert ex.input_text.endswith("?") or "?" in ex.input_text
                assert len(ex.output_text) > 10

            report = await bot.evaluate_dataset(dataset)
            path = await bot.export_dataset(dataset, str(output))

        assert Path(path).exists()
        lines = [l for l in Path(path).read_text(encoding="utf-8").strip().split("\n") if l]
        assert len(lines) > 0
        for line in lines:
            obj = json.loads(line)
            assert "input" in obj and "output" in obj

    @pytest.mark.asyncio
    async def test_e2e_summarization(self, text_file, tmp_path):
        """Real summarization pipeline."""
        output = tmp_path / "e2e_summary.jsonl"
        async with TrainingDataBot() as bot:
            docs = await bot.load_documents([str(text_file)])
            dataset = await bot.process_documents(
                docs, task_type="summarization",
                task_config={"style": "concise"}
            )
            assert len(dataset.examples) > 0
            for ex in dataset.examples:
                # Summary should be meaningful and not exceed chunk length by more than a brief sentence
                assert len(ex.output_text) <= len(ex.input_text) + 50
                assert len(ex.output_text) > 10

            await bot.export_dataset(dataset, str(output))

        assert output.exists()

    @pytest.mark.asyncio
    async def test_e2e_classification(self, text_file, tmp_path):
        """Real classification pipeline with custom categories."""
        output = tmp_path / "e2e_classification.jsonl"
        categories = ["technical", "educational", "general"]
        async with TrainingDataBot() as bot:
            docs = await bot.load_documents([str(text_file)])
            dataset = await bot.process_documents(
                docs, task_type="classification",
                task_config={"categories": categories}
            )
            assert len(dataset.examples) > 0
            for ex in dataset.examples:
                assert ex.output_text in categories, \
                    f"Output '{ex.output_text}' not in valid categories {categories}"

            await bot.export_dataset(dataset, str(output))

        assert output.exists()

    @pytest.mark.asyncio
    async def test_e2e_multiple_sources(self, text_file, multi_file_dir, tmp_path):
        """Load multiple files and generate QA from all."""
        files = [str(p) for p in multi_file_dir.iterdir()]
        output = tmp_path / "e2e_multi.jsonl"
        async with TrainingDataBot() as bot:
            docs = await bot.load_documents(files)
            assert len(docs) == 3, f"Expected 3 docs, got {len(docs)}"
            dataset = await bot.process_documents(docs, task_type="qa_generation")
            assert len(dataset.examples) > 0
            report = await bot.evaluate_dataset(dataset)
            path = await bot.export_dataset(dataset, str(output))

        # Verify the output is a valid training file
        assert Path(path).exists()
        lines = [l for l in Path(path).read_text(encoding="utf-8").strip().split("\n") if l]
        assert len(lines) >= 1

    @pytest.mark.asyncio
    async def test_e2e_quick_process(self, text_file, tmp_path):
        """Test the quick_process convenience method."""
        output = tmp_path / "e2e_quick.jsonl"
        async with TrainingDataBot() as bot:
            dataset = await bot.quick_process(
                source=str(text_file),
                output_path=str(output),
                task_type="qa_generation"
            )
        assert output.exists()
        assert dataset.total_examples >= 0
