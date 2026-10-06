"""
Pytest configuration and shared fixtures for all tests.
"""
import sys
import os
import asyncio
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))
os.chdir(Path(__file__).parent.parent)

from tests.fixtures.sample_content import (
    SAMPLE_TEXT, SAMPLE_HTML, SAMPLE_MARKDOWN,
    SAMPLE_JSON, SAMPLE_CSV
)
from training_data_bot.core.models import (
    Document, TextChunk, TrainingExample, Dataset, TaskTemplate,
    TaskResult, QualityReport, DocumentType, TaskType
)


# -------------------------------------------------------
# Fixture files on disk
# -------------------------------------------------------

@pytest.fixture(scope="session")
def fixtures_dir(tmp_path_factory):
    """Create all test fixture files on disk."""
    d = tmp_path_factory.mktemp("fixtures")

    # Text file
    (d / "sample.txt").write_text(SAMPLE_TEXT, encoding="utf-8")

    # Markdown
    (d / "sample.md").write_text(SAMPLE_MARKDOWN, encoding="utf-8")

    # HTML
    (d / "sample.html").write_text(SAMPLE_HTML, encoding="utf-8")

    # JSON
    (d / "sample.json").write_text(SAMPLE_JSON, encoding="utf-8")

    # CSV
    (d / "sample.csv").write_text(SAMPLE_CSV, encoding="utf-8")

    return d


# -------------------------------------------------------
# Model fixtures
# -------------------------------------------------------

@pytest.fixture
def sample_document():
    """A basic Document for testing."""
    return Document(
        title="Test Document",
        content=SAMPLE_TEXT,
        source="test.txt",
        doc_type=DocumentType.TXT,
        word_count=len(SAMPLE_TEXT.split()),
        char_count=len(SAMPLE_TEXT)
    )


@pytest.fixture
def sample_chunk(sample_document):
    """A TextChunk from the sample document."""
    return TextChunk(
        document_id=sample_document.id,
        content=SAMPLE_TEXT[:500],
        start_index=0,
        end_index=500,
        chunk_index=0,
        token_count=125
    )


@pytest.fixture
def sample_training_example(sample_document):
    """A single TrainingExample."""
    return TrainingExample(
        input_text="What is machine learning?",
        output_text="Machine learning is a subset of AI that enables systems to learn from experience.",
        task_type=TaskType.QA_GENERATION,
        source_document_id=sample_document.id
    )


@pytest.fixture
def sample_dataset(sample_document):
    """A Dataset with 10 examples."""
    examples = [
        TrainingExample(
            input_text=f"Question {i}: What is concept {i}?",
            output_text=f"Answer {i}: Concept {i} is an important part of machine learning.",
            task_type=TaskType.QA_GENERATION,
            source_document_id=sample_document.id
        )
        for i in range(10)
    ]
    return Dataset(
        name="test_dataset",
        description="Test dataset",
        examples=examples,
        total_examples=10
    )


# -------------------------------------------------------
# Mock AI client
# -------------------------------------------------------

QA_MOCK_RESPONSE = """Q1: What is machine learning?
A1: Machine learning is a subset of artificial intelligence that enables systems to learn from experience.

Q2: What are the types of machine learning?
A2: There are three main types: supervised learning, unsupervised learning, and reinforcement learning.

Q3: What are some applications of machine learning?
A3: Applications include image recognition, natural language processing, and recommendation systems."""

CLASSIFICATION_MOCK_RESPONSE = """Category: technical
Explanation: The text discusses technical concepts related to machine learning and AI.
Confidence: high"""

SUMMARIZATION_MOCK_RESPONSE = """Machine learning is a subset of AI that allows systems to learn from data without explicit programming. It includes supervised, unsupervised, and reinforcement learning, with applications in image recognition, NLP, and autonomous vehicles."""


@pytest.fixture
def mock_ai_client():
    """Mock AIClient that returns canned responses without real API calls."""
    with patch("training_data_bot.ai.client.AIClient.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = QA_MOCK_RESPONSE
        yield mock_gen


@pytest.fixture
def mock_ai_classification():
    """Mock AIClient returning classification responses."""
    with patch("training_data_bot.ai.client.AIClient.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = CLASSIFICATION_MOCK_RESPONSE
        yield mock_gen


@pytest.fixture
def mock_ai_summarization():
    """Mock AIClient returning summarization responses."""
    with patch("training_data_bot.ai.client.AIClient.generate", new_callable=AsyncMock) as mock_gen:
        mock_gen.return_value = SUMMARIZATION_MOCK_RESPONSE
        yield mock_gen
