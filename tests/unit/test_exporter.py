"""
Unit Tests: Dataset Exporter
Tests JSONL, JSON, CSV export, split export, format detection, and metadata handling.
"""
import sys
import os
import json
import csv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.chdir(Path(__file__).parent.parent.parent)

import pytest
from uuid import uuid4

from training_data_bot.storage.exporter import DatasetExporter
from training_data_bot.core.models import (
    Dataset, TrainingExample, TaskType, ExportFormat
)


def make_dataset(n: int = 10, task_type: TaskType = TaskType.QA_GENERATION) -> Dataset:
    """Create a test dataset with n examples."""
    doc_id = uuid4()
    examples = [
        TrainingExample(
            input_text=f"Question {i}: What is concept {i}?",
            output_text=f"Concept {i} is part of machine learning.",
            task_type=task_type,
            source_document_id=doc_id
        )
        for i in range(n)
    ]
    return Dataset(
        name="test_dataset",
        description="A test dataset",
        examples=examples,
        total_examples=n
    )


class TestExporterInit:
    def test_default_include_metadata(self):
        exporter = DatasetExporter()
        # Should match settings default (True)
        assert isinstance(exporter.include_metadata, bool)

    def test_override_include_metadata(self):
        exporter = DatasetExporter(include_metadata=False)
        assert exporter.include_metadata is False

    def test_repr(self):
        exporter = DatasetExporter(include_metadata=True)
        assert "include_metadata=True" in repr(exporter)


class TestFormatDetection:
    def test_jsonl_extension(self):
        exporter = DatasetExporter()
        fmt = exporter._detect_format(Path("output.jsonl"))
        assert fmt == ExportFormat.JSONL

    def test_json_extension(self):
        exporter = DatasetExporter()
        fmt = exporter._detect_format(Path("data.json"))
        assert fmt == ExportFormat.JSON

    def test_csv_extension(self):
        exporter = DatasetExporter()
        fmt = exporter._detect_format(Path("data.csv"))
        assert fmt == ExportFormat.CSV

    def test_unknown_extension_defaults_jsonl(self):
        exporter = DatasetExporter()
        fmt = exporter._detect_format(Path("data.xyz"))
        assert fmt == ExportFormat.JSONL

    def test_uppercase_extension(self):
        """Extensions should be matched case-insensitively."""
        exporter = DatasetExporter()
        fmt = exporter._detect_format(Path("data.JSONL"))
        assert fmt == ExportFormat.JSONL


class TestSplitExamples:
    def test_80_10_10_split(self):
        """Default 80/10/10 split is respected."""
        ds = make_dataset(100)
        exporter = DatasetExporter()
        train, val, test = exporter._split_examples(ds)
        assert len(train) == 80
        assert len(val) == 10
        assert len(test) == 10
        assert len(train) + len(val) + len(test) == 100

    def test_small_dataset(self):
        """Small datasets still split without error."""
        ds = make_dataset(3)
        exporter = DatasetExporter()
        train, val, test = exporter._split_examples(ds)
        assert len(train) + len(val) + len(test) == 3

    def test_custom_split(self):
        """Custom split ratios are respected."""
        ds = make_dataset(10)
        ds.train_split = 0.6
        ds.validation_split = 0.2
        ds.test_split = 0.2
        exporter = DatasetExporter()
        train, val, test = exporter._split_examples(ds)
        assert len(train) == 6
        assert len(val) == 2
        assert len(test) == 2


class TestJSONLExport:
    @pytest.mark.asyncio
    async def test_creates_file(self, tmp_path):
        exporter = DatasetExporter(include_metadata=False)
        ds = make_dataset(5)
        out = tmp_path / "output.jsonl"
        result = await exporter.export_dataset(ds, out)
        assert result == out
        assert out.exists()

    @pytest.mark.asyncio
    async def test_correct_line_count(self, tmp_path):
        """Each example becomes one line."""
        exporter = DatasetExporter(include_metadata=False)
        ds = make_dataset(5)
        out = tmp_path / "output.jsonl"
        await exporter.export_dataset(ds, out)
        lines = [l for l in out.read_text(encoding="utf-8").strip().split("\n") if l]
        assert len(lines) == 5

    @pytest.mark.asyncio
    async def test_each_line_is_valid_json(self, tmp_path):
        exporter = DatasetExporter(include_metadata=False)
        ds = make_dataset(3)
        out = tmp_path / "output.jsonl"
        await exporter.export_dataset(ds, out)
        for line in out.read_text(encoding="utf-8").strip().split("\n"):
            obj = json.loads(line)  # should not raise
            assert "input" in obj
            assert "output" in obj
            assert "task_type" in obj

    @pytest.mark.asyncio
    async def test_metadata_included_when_enabled(self, tmp_path):
        exporter = DatasetExporter(include_metadata=True)
        ds = make_dataset(2)
        out = tmp_path / "output.jsonl"
        await exporter.export_dataset(ds, out)
        lines = out.read_text(encoding="utf-8").strip().split("\n")
        obj = json.loads(lines[0])
        assert "metadata" in obj

    @pytest.mark.asyncio
    async def test_metadata_excluded_when_disabled(self, tmp_path):
        exporter = DatasetExporter(include_metadata=False)
        ds = make_dataset(2)
        out = tmp_path / "output.jsonl"
        await exporter.export_dataset(ds, out)
        lines = out.read_text(encoding="utf-8").strip().split("\n")
        obj = json.loads(lines[0])
        assert "metadata" not in obj

    @pytest.mark.asyncio
    async def test_output_dir_created(self, tmp_path):
        """Export creates parent directory if it doesn't exist."""
        exporter = DatasetExporter(include_metadata=False)
        ds = make_dataset(2)
        out = tmp_path / "new_dir" / "output.jsonl"
        await exporter.export_dataset(ds, out)
        assert out.exists()

    @pytest.mark.asyncio
    async def test_auto_detect_format_from_extension(self, tmp_path):
        """Format auto-detected from file extension."""
        exporter = DatasetExporter(include_metadata=False)
        ds = make_dataset(2)
        out = tmp_path / "data.jsonl"
        await exporter.export_dataset(ds, out, format=None)
        assert out.exists()
        # Verify it's valid JSONL
        json.loads(out.read_text(encoding="utf-8").strip().split("\n")[0])


class TestJSONExport:
    @pytest.mark.asyncio
    async def test_creates_valid_json(self, tmp_path):
        exporter = DatasetExporter(include_metadata=False)
        ds = make_dataset(3)
        out = tmp_path / "output.json"
        await exporter.export_dataset(ds, out, format="json")
        data = json.loads(out.read_text(encoding="utf-8"))
        assert "name" in data
        assert "examples" in data
        assert len(data["examples"]) == 3

    @pytest.mark.asyncio
    async def test_example_fields(self, tmp_path):
        exporter = DatasetExporter(include_metadata=False)
        ds = make_dataset(1)
        out = tmp_path / "output.json"
        await exporter.export_dataset(ds, out, format="json")
        data = json.loads(out.read_text(encoding="utf-8"))
        ex = data["examples"][0]
        assert "input" in ex
        assert "output" in ex
        assert "task_type" in ex


class TestCSVExport:
    @pytest.mark.asyncio
    async def test_creates_valid_csv(self, tmp_path):
        exporter = DatasetExporter(include_metadata=False)
        ds = make_dataset(3)
        out = tmp_path / "output.csv"
        await exporter.export_dataset(ds, out, format="csv")
        assert out.exists()
        with open(out, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert len(rows) == 3

    @pytest.mark.asyncio
    async def test_csv_headers(self, tmp_path):
        exporter = DatasetExporter(include_metadata=False)
        ds = make_dataset(1)
        out = tmp_path / "output.csv"
        await exporter.export_dataset(ds, out, format="csv")
        with open(out, encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)
        assert "input_text" in headers
        assert "output_text" in headers
        assert "task_type" in headers

    @pytest.mark.asyncio
    async def test_content_preserved(self, tmp_path):
        """Verify actual content survives round-trip."""
        exporter = DatasetExporter(include_metadata=False)
        ds = make_dataset(1)
        first_input = ds.examples[0].input_text
        out = tmp_path / "output.csv"
        await exporter.export_dataset(ds, out, format="csv")
        with open(out, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        assert rows[0]["input_text"] == first_input


class TestSplitExport:
    @pytest.mark.asyncio
    async def test_creates_three_files(self, tmp_path):
        exporter = DatasetExporter(include_metadata=False)
        ds = make_dataset(10)
        paths = await exporter.export_split_dataset(ds, tmp_path, format="jsonl")
        assert "train" in paths
        assert "val" in paths
        assert "test" in paths

    @pytest.mark.asyncio
    async def test_correct_sizes(self, tmp_path):
        exporter = DatasetExporter(include_metadata=False)
        ds = make_dataset(10)
        paths = await exporter.export_split_dataset(ds, tmp_path, format="jsonl")
        train_lines = paths["train"].read_text(encoding="utf-8").strip().split("\n")
        assert len(train_lines) == 8  # 80% of 10

    @pytest.mark.asyncio
    async def test_all_files_are_valid_jsonl(self, tmp_path):
        exporter = DatasetExporter(include_metadata=False)
        ds = make_dataset(10)
        paths = await exporter.export_split_dataset(ds, tmp_path, format="jsonl")
        for split, path in paths.items():
            for line in path.read_text(encoding="utf-8").strip().split("\n"):
                if line:
                    json.loads(line)  # Must not raise
