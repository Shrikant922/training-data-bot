"""
Dataset Exporter - Training Data Export

Exports training datasets to various formats (JSONL, JSON, CSV) for LLM fine-tuning.
"""

import json
from pathlib import Path
from typing import List, Optional, Union

import aiofiles

from ..core.config import settings
from ..core.exceptions import ExportError, InvalidFormatError
from ..core.logging import get_logger
from ..core.models import Dataset, ExportFormat, TrainingExample


class DatasetExporter:
    """
    Exports training datasets to standard formats.

    Supports:
    - JSONL (JSON Lines) - one example per line
    - JSON - single JSON file with all examples
    - CSV - comma-separated values
    """

    def __init__(self, include_metadata: bool = None):
        """
        Initialize the dataset exporter.

        Args:
            include_metadata: Include metadata in exports (uses settings if None)
        """
        self.logger = get_logger("exporter")
        self.include_metadata = (
            include_metadata if include_metadata is not None
            else settings.export_include_metadata
        )

        self.logger.info(f"Dataset exporter initialized (metadata={self.include_metadata})")

    async def export_dataset(
        self,
        dataset: Dataset,
        output_path: Union[str, Path],
        format: Union[str, ExportFormat] = None
    ) -> Path:
        """
        Export a dataset to file.

        Args:
            dataset: Dataset to export
            output_path: Output file path
            format: Export format (auto-detected from extension if not provided)

        Returns:
            Path to exported file

        Example:
            exporter = DatasetExporter()
            path = await exporter.export_dataset(dataset, "training_data.jsonl")
        """
        output_path = Path(output_path)

        # Determine format
        if format is None:
            format = self._detect_format(output_path)
        elif isinstance(format, str):
            format = ExportFormat(format.lower())

        self.logger.info(
            f"Exporting dataset '{dataset.name}' to {output_path} "
            f"(format={format.value}, examples={len(dataset.examples)})"
        )

        # Create output directory if needed
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            # Route to appropriate exporter
            if format == ExportFormat.JSONL:
                await self._export_jsonl(dataset, output_path)
            elif format == ExportFormat.JSON:
                await self._export_json(dataset, output_path)
            elif format == ExportFormat.CSV:
                await self._export_csv(dataset, output_path)
            else:
                raise InvalidFormatError(
                    f"Unsupported export format: {format}",
                    details={"format": format.value}
                )

            self.logger.info(f"Export complete: {output_path}")
            return output_path

        except Exception as e:
            if isinstance(e, ExportError):
                raise
            raise ExportError(
                f"Failed to export dataset",
                details={
                    "dataset": dataset.name,
                    "output_path": str(output_path),
                    "format": format.value
                },
                original_error=e
            )

    async def export_split_dataset(
        self,
        dataset: Dataset,
        output_dir: Union[str, Path],
        format: Union[str, ExportFormat] = None,
        split_names: Optional[tuple[str, str, str]] = None
    ) -> dict[str, Path]:
        """
        Export dataset split into train/validation/test files.

        Args:
            dataset: Dataset to export
            output_dir: Output directory
            format: Export format
            split_names: Custom names for splits (train, val, test)

        Returns:
            Dictionary mapping split names to file paths

        Example:
            paths = await exporter.export_split_dataset(
                dataset,
                "output/",
                format="jsonl"
            )
            # Returns: {"train": "output/train.jsonl", "val": ..., "test": ...}
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        # Default split names
        split_names = split_names or ("train", "val", "test")

        # Determine format
        if format is None:
            format = ExportFormat(settings.default_export_format)
        elif isinstance(format, str):
            format = ExportFormat(format.lower())

        self.logger.info(f"Exporting split dataset to {output_dir}")

        # Split the dataset
        train_examples, val_examples, test_examples = self._split_examples(dataset)

        # Create split datasets
        splits = {
            split_names[0]: Dataset(
                name=f"{dataset.name}_train",
                description=f"Training split of {dataset.name}",
                examples=train_examples,
                total_examples=len(train_examples)
            ),
            split_names[1]: Dataset(
                name=f"{dataset.name}_val",
                description=f"Validation split of {dataset.name}",
                examples=val_examples,
                total_examples=len(val_examples)
            ),
            split_names[2]: Dataset(
                name=f"{dataset.name}_test",
                description=f"Test split of {dataset.name}",
                examples=test_examples,
                total_examples=len(test_examples)
            ),
        }

        # Export each split
        paths = {}
        extension = f".{format.value}"

        for split_name, split_dataset in splits.items():
            if len(split_dataset.examples) > 0:
                output_path = output_dir / f"{split_name}{extension}"
                await self.export_dataset(split_dataset, output_path, format)
                paths[split_name] = output_path

        self.logger.info(f"Split export complete: {len(paths)} files")
        return paths

    async def _export_jsonl(self, dataset: Dataset, output_path: Path) -> None:
        """Export to JSONL format (one JSON per line)."""
        async with aiofiles.open(output_path, mode='w', encoding='utf-8') as f:
            for example in dataset.examples:
                example_dict = self._example_to_dict(example)
                json_line = json.dumps(example_dict, ensure_ascii=False)
                await f.write(json_line + '\n')

    async def _export_json(self, dataset: Dataset, output_path: Path) -> None:
        """Export to JSON format (single JSON file)."""
        data = {
            "name": dataset.name,
            "description": dataset.description,
            "total_examples": len(dataset.examples),
            "examples": [self._example_to_dict(ex) for ex in dataset.examples]
        }

        if self.include_metadata:
            data["metadata"] = dataset.metadata

        async with aiofiles.open(output_path, mode='w', encoding='utf-8') as f:
            json_str = json.dumps(data, indent=2, ensure_ascii=False)
            await f.write(json_str)

    async def _export_csv(self, dataset: Dataset, output_path: Path) -> None:
        """Export to CSV format."""
        import csv

        # Write CSV synchronously (aiofiles doesn't support csv module well)
        def write_csv():
            with open(output_path, mode='w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)

                # Header
                headers = ["input_text", "output_text", "task_type"]
                if self.include_metadata:
                    headers.extend(["source_document_id", "quality_score"])
                writer.writerow(headers)

                # Rows
                for example in dataset.examples:
                    row = [
                        example.input_text,
                        example.output_text,
                        example.task_type.value
                    ]

                    if self.include_metadata:
                        row.extend([
                            str(example.source_document_id),
                            str(example.quality_scores.get("overall", ""))
                        ])

                    writer.writerow(row)

        # Run in thread pool
        import asyncio
        await asyncio.to_thread(write_csv)

    def _example_to_dict(self, example: TrainingExample) -> dict:
        """Convert TrainingExample to dictionary for export."""
        data = {
            "input": example.input_text,
            "output": example.output_text,
            "task_type": example.task_type.value,
        }

        if self.include_metadata:
            data["metadata"] = {
                "id": str(example.id),
                "source_document_id": str(example.source_document_id),
                "quality_scores": example.quality_scores,
                **example.metadata
            }

        return data

    def _split_examples(
        self,
        dataset: Dataset
    ) -> tuple[List[TrainingExample], List[TrainingExample], List[TrainingExample]]:
        """Split examples into train/val/test sets."""
        total = len(dataset.examples)

        train_size = int(total * dataset.train_split)
        val_size = int(total * dataset.validation_split)

        train = dataset.examples[:train_size]
        val = dataset.examples[train_size:train_size + val_size]
        test = dataset.examples[train_size + val_size:]

        return train, val, test

    def _detect_format(self, path: Path) -> ExportFormat:
        """Detect export format from file extension."""
        suffix = path.suffix.lower().lstrip('.')

        if suffix == 'jsonl':
            return ExportFormat.JSONL
        elif suffix == 'json':
            return ExportFormat.JSON
        elif suffix == 'csv':
            return ExportFormat.CSV
        else:
            # Default to JSONL
            return ExportFormat.JSONL

    def __repr__(self) -> str:
        """String representation."""
        return f"DatasetExporter(include_metadata={self.include_metadata})"
