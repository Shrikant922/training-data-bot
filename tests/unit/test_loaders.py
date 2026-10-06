"""
Unit Tests: Document Loaders
Tests BaseLoader, DocumentLoader (txt/md/html/json/csv), PDFLoader, and UnifiedLoader.
"""
import sys
import os
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.chdir(Path(__file__).parent.parent.parent)

import pytest
from uuid import uuid4

from training_data_bot.sources.base import BaseLoader
from training_data_bot.sources.document import DocumentLoader
from training_data_bot.sources.pdf import PDFLoader
from training_data_bot.sources.web import WebLoader
from training_data_bot.sources.unified import UnifiedLoader
from training_data_bot.core.models import Document, DocumentType
from training_data_bot.core.exceptions import DocumentLoadError
from tests.fixtures.sample_content import (
    SAMPLE_TEXT, SAMPLE_HTML, SAMPLE_MARKDOWN, SAMPLE_JSON, SAMPLE_CSV
)


# ---------------------------------------------------------------------------
# Fixtures: create real files on disk
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def text_file(tmp_path_factory):
    p = tmp_path_factory.mktemp("docs") / "sample.txt"
    p.write_text(SAMPLE_TEXT, encoding="utf-8")
    return p

@pytest.fixture(scope="module")
def md_file(tmp_path_factory):
    p = tmp_path_factory.mktemp("docs") / "sample.md"
    p.write_text(SAMPLE_MARKDOWN, encoding="utf-8")
    return p

@pytest.fixture(scope="module")
def html_file(tmp_path_factory):
    p = tmp_path_factory.mktemp("docs") / "sample.html"
    p.write_text(SAMPLE_HTML, encoding="utf-8")
    return p

@pytest.fixture(scope="module")
def json_file(tmp_path_factory):
    p = tmp_path_factory.mktemp("docs") / "sample.json"
    p.write_text(SAMPLE_JSON, encoding="utf-8")
    return p

@pytest.fixture(scope="module")
def csv_file(tmp_path_factory):
    p = tmp_path_factory.mktemp("docs") / "sample.csv"
    p.write_text(SAMPLE_CSV, encoding="utf-8")
    return p


# ---------------------------------------------------------------------------
# BaseLoader tests (via DocumentLoader which extends it)
# ---------------------------------------------------------------------------

class TestBaseLoaderCreateDocument:
    def test_creates_document_with_correct_fields(self, text_file):
        loader = DocumentLoader()
        doc = loader.create_document(
            title="Test",
            content="Hello world",
            source=text_file,
            doc_type=DocumentType.TXT
        )
        assert isinstance(doc, Document)
        assert doc.title == "Test"
        assert doc.content == "Hello world"
        assert doc.word_count == 2
        assert doc.char_count == 11

    def test_word_count_accuracy(self, text_file):
        loader = DocumentLoader()
        content = "the quick brown fox jumps"
        doc = loader.create_document(
            title="t", content=content,
            source=text_file, doc_type=DocumentType.TXT
        )
        assert doc.word_count == 5

    def test_metadata_contains_loader_name(self, text_file):
        loader = DocumentLoader()
        doc = loader.create_document(
            title="t", content="content",
            source=text_file, doc_type=DocumentType.TXT
        )
        assert "loader" in doc.metadata
        assert "DocumentLoader" in doc.metadata["loader"]

    def test_metadata_contains_loaded_at(self, text_file):
        loader = DocumentLoader()
        doc = loader.create_document(
            title="t", content="content",
            source=text_file, doc_type=DocumentType.TXT
        )
        assert "loaded_at" in doc.metadata


class TestBaseLoaderGetDocumentType:
    def test_http_url_is_url_type(self):
        loader = DocumentLoader()
        assert loader.get_document_type("http://example.com") == DocumentType.URL

    def test_https_url_is_url_type(self):
        loader = DocumentLoader()
        assert loader.get_document_type("https://example.com/page") == DocumentType.URL

    def test_pdf_extension(self):
        loader = DocumentLoader()
        assert loader.get_document_type("document.pdf") == DocumentType.PDF

    def test_txt_extension(self):
        loader = DocumentLoader()
        assert loader.get_document_type("notes.txt") == DocumentType.TXT

    def test_csv_extension(self):
        loader = DocumentLoader()
        assert loader.get_document_type("data.csv") == DocumentType.CSV

    def test_unsupported_extension_raises(self):
        loader = DocumentLoader()
        with pytest.raises(DocumentLoadError):
            loader.get_document_type("file.exe")

    def test_no_extension_raises(self):
        loader = DocumentLoader()
        with pytest.raises(DocumentLoadError):
            loader.get_document_type("noextension")


class TestBaseLoaderValidateFile:
    def test_existing_file_passes(self, text_file):
        loader = DocumentLoader()
        loader.validate_file_exists(text_file)  # Should not raise

    def test_missing_file_raises(self):
        loader = DocumentLoader()
        with pytest.raises(DocumentLoadError):
            loader.validate_file_exists(Path("/nonexistent/file.txt"))

    def test_directory_raises(self, tmp_path):
        loader = DocumentLoader()
        with pytest.raises(DocumentLoadError):
            loader.validate_file_exists(tmp_path)  # It's a directory


# ---------------------------------------------------------------------------
# DocumentLoader tests
# ---------------------------------------------------------------------------

class TestDocumentLoaderTXT:
    @pytest.mark.asyncio
    async def test_loads_txt_file(self, text_file):
        loader = DocumentLoader()
        doc = await loader.load_single(text_file)
        assert isinstance(doc, Document)
        assert doc.doc_type == DocumentType.TXT
        assert len(doc.content) > 0

    @pytest.mark.asyncio
    async def test_content_contains_expected_text(self, text_file):
        loader = DocumentLoader()
        doc = await loader.load_single(text_file)
        assert "machine learning" in doc.content.lower()

    @pytest.mark.asyncio
    async def test_word_count_populated(self, text_file):
        loader = DocumentLoader()
        doc = await loader.load_single(text_file)
        assert doc.word_count > 0

    @pytest.mark.asyncio
    async def test_missing_file_raises(self, tmp_path):
        loader = DocumentLoader()
        with pytest.raises(DocumentLoadError):
            await loader.load_single(tmp_path / "nonexistent.txt")


class TestDocumentLoaderMarkdown:
    @pytest.mark.asyncio
    async def test_loads_md_file(self, md_file):
        loader = DocumentLoader()
        doc = await loader.load_single(md_file)
        assert doc.doc_type == DocumentType.MD
        assert len(doc.content) > 0

    @pytest.mark.asyncio
    async def test_md_content_preserved(self, md_file):
        loader = DocumentLoader()
        doc = await loader.load_single(md_file)
        assert "Deep Learning" in doc.content


class TestDocumentLoaderHTML:
    @pytest.mark.asyncio
    async def test_loads_html_file(self, html_file):
        loader = DocumentLoader()
        doc = await loader.load_single(html_file)
        assert doc.doc_type == DocumentType.HTML
        assert len(doc.content) > 0

    @pytest.mark.asyncio
    async def test_html_tags_stripped(self, html_file):
        loader = DocumentLoader()
        doc = await loader.load_single(html_file)
        # HTML tags should be stripped
        assert "<html>" not in doc.content
        assert "<body>" not in doc.content


class TestDocumentLoaderJSON:
    @pytest.mark.asyncio
    async def test_loads_json_file(self, json_file):
        loader = DocumentLoader()
        doc = await loader.load_single(json_file)
        assert doc.doc_type == DocumentType.JSON
        assert len(doc.content) > 0

    @pytest.mark.asyncio
    async def test_json_content_readable(self, json_file):
        loader = DocumentLoader()
        doc = await loader.load_single(json_file)
        # Content should contain the data from the JSON
        assert "AI" in doc.content or "artificial" in doc.content.lower()


class TestDocumentLoaderCSV:
    @pytest.mark.asyncio
    async def test_loads_csv_file(self, csv_file):
        loader = DocumentLoader()
        doc = await loader.load_single(csv_file)
        assert doc.doc_type == DocumentType.CSV
        assert len(doc.content) > 0

    @pytest.mark.asyncio
    async def test_csv_data_in_content(self, csv_file):
        loader = DocumentLoader()
        doc = await loader.load_single(csv_file)
        # Should contain text from CSV rows
        assert "Python" in doc.content or "AI" in doc.content


# ---------------------------------------------------------------------------
# PDFLoader tests
# ---------------------------------------------------------------------------

class TestPDFLoader:
    @pytest.mark.asyncio
    async def test_missing_pdf_raises(self, tmp_path):
        loader = PDFLoader()
        with pytest.raises(DocumentLoadError):
            await loader.load_single(tmp_path / "nonexistent.pdf")

    def test_supported_format_is_pdf(self):
        loader = PDFLoader()
        assert DocumentType.PDF in loader.supported_formats

    @pytest.mark.asyncio
    async def test_real_pdf_loads_if_exists(self):
        """If the tutorial PDF exists, verify it loads correctly."""
        pdf_path = Path("Production AI Tutorial.pdf")
        if not pdf_path.exists():
            pytest.skip("Tutorial PDF not available")
        loader = PDFLoader()
        doc = await loader.load_single(pdf_path)
        assert doc.doc_type == DocumentType.PDF
        assert len(doc.content) > 100
        assert doc.word_count > 10


# ---------------------------------------------------------------------------
# UnifiedLoader tests
# ---------------------------------------------------------------------------

class TestUnifiedLoader:
    def test_instantiates(self):
        loader = UnifiedLoader()
        assert loader is not None

    @pytest.mark.asyncio
    async def test_routes_txt_to_document_loader(self, text_file):
        loader = UnifiedLoader()
        docs = await loader.load_multiple([str(text_file)])
        assert len(docs) == 1
        assert docs[0].doc_type == DocumentType.TXT

    @pytest.mark.asyncio
    async def test_routes_csv_to_document_loader(self, csv_file):
        loader = UnifiedLoader()
        docs = await loader.load_multiple([str(csv_file)])
        assert len(docs) == 1
        assert docs[0].doc_type == DocumentType.CSV

    @pytest.mark.asyncio
    async def test_loads_multiple_files_parallel(self, text_file, md_file, csv_file):
        loader = UnifiedLoader()
        docs = await loader.load_multiple([str(text_file), str(md_file), str(csv_file)])
        assert len(docs) == 3

    @pytest.mark.asyncio
    async def test_missing_file_skipped_not_crash(self, text_file, tmp_path):
        """A missing file is skipped; other files still load."""
        loader = UnifiedLoader()
        missing = str(tmp_path / "missing.txt")
        docs = await loader.load_multiple([str(text_file), missing])
        # At least the valid file loaded
        assert len(docs) >= 1


# ---------------------------------------------------------------------------
# BaseLoader load_multiple parallel tests
# ---------------------------------------------------------------------------

class TestLoadMultiple:
    @pytest.mark.asyncio
    async def test_loads_all_files(self, text_file, md_file):
        loader = DocumentLoader()
        docs = await loader.load_multiple([text_file, md_file])
        assert len(docs) == 2

    @pytest.mark.asyncio
    async def test_partial_failure_doesnt_crash(self, text_file, tmp_path):
        """Missing file is skipped, valid file still returned."""
        loader = DocumentLoader()
        missing = tmp_path / "missing.txt"
        docs = await loader.load_multiple([text_file, missing])
        assert len(docs) >= 1  # The valid file succeeded

    @pytest.mark.asyncio
    async def test_respects_max_workers(self, text_file, md_file, csv_file):
        """load_multiple with max_workers=1 still returns all docs."""
        loader = DocumentLoader()
        docs = await loader.load_multiple([text_file, md_file, csv_file], max_workers=1)
        assert len(docs) == 3
