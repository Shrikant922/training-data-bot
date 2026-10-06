"""
Unit Tests: Core Data Models
Tests all Pydantic models, enums, and their validation logic.
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.chdir(Path(__file__).parent.parent.parent)

import pytest
from uuid import UUID, uuid4
from datetime import datetime

from training_data_bot.core.models import (
    BaseEntity, Document, TextChunk, TrainingExample, Dataset,
    TaskTemplate, TaskResult, QualityReport, ProcessingJob,
    DocumentType, TaskType, QualityMetric, ProcessingStatus, ExportFormat
)


class TestBaseEntity:
    def test_auto_uuid(self):
        """BaseEntity automatically generates a UUID id."""
        e = TrainingExample(
            input_text="q", output_text="a",
            task_type=TaskType.QA_GENERATION, source_document_id=uuid4()
        )
        assert isinstance(e.id, UUID)

    def test_auto_created_at(self):
        """BaseEntity automatically sets created_at timestamp."""
        before = datetime.utcnow()
        e = Dataset(name="x", description="y")
        after = datetime.utcnow()
        assert before <= e.created_at <= after

    def test_updated_at_defaults_none(self):
        """updated_at is None by default."""
        e = Dataset(name="x", description="y")
        assert e.updated_at is None

    def test_metadata_defaults_empty_dict(self):
        """metadata defaults to empty dict."""
        e = Dataset(name="x", description="y")
        assert e.metadata == {}

    def test_each_entity_has_unique_id(self):
        """Two entities get different UUIDs."""
        e1 = Dataset(name="a", description="a")
        e2 = Dataset(name="b", description="b")
        assert e1.id != e2.id


class TestDocumentType:
    def test_all_values(self):
        assert DocumentType.PDF == "pdf"
        assert DocumentType.DOCX == "docx"
        assert DocumentType.TXT == "txt"
        assert DocumentType.MD == "md"
        assert DocumentType.HTML == "html"
        assert DocumentType.JSON == "json"
        assert DocumentType.CSV == "csv"
        assert DocumentType.URL == "url"

    def test_from_string(self):
        assert DocumentType("pdf") == DocumentType.PDF
        assert DocumentType("url") == DocumentType.URL

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            DocumentType("exe")


class TestTaskType:
    def test_all_values(self):
        assert TaskType.QA_GENERATION == "qa_generation"
        assert TaskType.CLASSIFICATION == "classification"
        assert TaskType.SUMMARIZATION == "summarization"
        assert TaskType.NER == "named_entity_recognition"
        assert TaskType.RED_TEAMING == "red_teaming"
        assert TaskType.INSTRUCTION_RESPONSE == "instruction_response"


class TestExportFormat:
    def test_all_values(self):
        assert ExportFormat.JSONL == "jsonl"
        assert ExportFormat.JSON == "json"
        assert ExportFormat.CSV == "csv"


class TestProcessingStatus:
    def test_all_values(self):
        assert ProcessingStatus.PENDING == "pending"
        assert ProcessingStatus.PROCESSING == "processing"
        assert ProcessingStatus.COMPLETED == "completed"
        assert ProcessingStatus.FAILED == "failed"


class TestDocument:
    def test_creation(self):
        doc = Document(
            title="Test Doc",
            content="Hello world test document",
            source="test.txt",
            doc_type=DocumentType.TXT,
            word_count=4,
            char_count=25
        )
        assert doc.title == "Test Doc"
        assert doc.doc_type == DocumentType.TXT
        assert doc.word_count == 4

    def test_required_fields(self):
        """Missing required fields raise ValidationError."""
        with pytest.raises(Exception):
            Document(title="x")  # missing content, source, etc.

    def test_content_stored(self):
        doc = Document(
            title="t", content="Some content here",
            source="x.txt", doc_type=DocumentType.TXT,
            word_count=3, char_count=17
        )
        assert doc.content == "Some content here"


class TestTextChunk:
    def test_creation(self):
        doc_id = uuid4()
        chunk = TextChunk(
            document_id=doc_id,
            content="chunk text",
            start_index=0,
            end_index=10,
            chunk_index=0,
            token_count=3
        )
        assert chunk.document_id == doc_id
        assert chunk.content == "chunk text"
        assert chunk.chunk_index == 0

    def test_end_index_greater_than_start(self):
        """Verify indices are stored as provided."""
        doc_id = uuid4()
        chunk = TextChunk(
            document_id=doc_id, content="abc",
            start_index=100, end_index=103,
            chunk_index=5, token_count=1
        )
        assert chunk.start_index == 100
        assert chunk.end_index == 103


class TestTrainingExample:
    def test_creation(self):
        doc_id = uuid4()
        ex = TrainingExample(
            input_text="What is AI?",
            output_text="AI is artificial intelligence.",
            task_type=TaskType.QA_GENERATION,
            source_document_id=doc_id
        )
        assert ex.input_text == "What is AI?"
        assert ex.output_text == "AI is artificial intelligence."
        assert ex.task_type == TaskType.QA_GENERATION

    def test_quality_scores_default_empty(self):
        doc_id = uuid4()
        ex = TrainingExample(
            input_text="q", output_text="a",
            task_type=TaskType.SUMMARIZATION,
            source_document_id=doc_id
        )
        assert ex.quality_scores == {}

    def test_source_chunk_id_optional(self):
        doc_id = uuid4()
        ex = TrainingExample(
            input_text="q", output_text="a",
            task_type=TaskType.CLASSIFICATION,
            source_document_id=doc_id
        )
        assert ex.source_chunk_id is None


class TestDataset:
    def test_creation_minimal(self):
        ds = Dataset(name="My Dataset", description="Test")
        assert ds.name == "My Dataset"
        assert ds.examples == []
        assert ds.total_examples == 0

    def test_default_splits(self):
        ds = Dataset(name="x", description="y")
        assert ds.train_split == 0.8
        assert ds.validation_split == 0.1
        assert ds.test_split == 0.1
        assert abs(ds.train_split + ds.validation_split + ds.test_split - 1.0) < 0.001

    def test_with_examples(self):
        doc_id = uuid4()
        examples = [
            TrainingExample(input_text=f"q{i}", output_text=f"a{i}",
                            task_type=TaskType.QA_GENERATION, source_document_id=doc_id)
            for i in range(5)
        ]
        ds = Dataset(name="x", description="y", examples=examples, total_examples=5)
        assert len(ds.examples) == 5
        assert ds.total_examples == 5


class TestQualityReport:
    def test_creation(self):
        target_id = uuid4()
        report = QualityReport(
            target_id=target_id,
            overall_score=0.85,
            passed=True
        )
        assert report.overall_score == 0.85
        assert report.passed is True
        assert report.issues == []
        assert report.warnings == []

    def test_failed_report(self):
        report = QualityReport(
            target_id=uuid4(),
            overall_score=0.4,
            passed=False,
            issues=["Low coherence score"],
            warnings=["Possible bias detected"]
        )
        assert report.passed is False
        assert len(report.issues) == 1
        assert len(report.warnings) == 1


class TestProcessingJob:
    def test_creation(self):
        job = ProcessingJob(name="Test Job", job_type="qa_generation")
        assert job.name == "Test Job"
        assert job.status == ProcessingStatus.PENDING
        assert job.total_items == 0
        assert job.processed_items == 0
        assert job.error_message is None

    def test_status_transition(self):
        job = ProcessingJob(name="x", job_type="y")
        job.status = ProcessingStatus.PROCESSING
        assert job.status == ProcessingStatus.PROCESSING

    def test_error_message_stored(self):
        job = ProcessingJob(name="x", job_type="y", error_message="Something failed")
        assert job.error_message == "Something failed"
