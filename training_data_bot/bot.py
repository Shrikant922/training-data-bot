"""
Training Data Bot - Main Orchestrator

The factory manager that coordinates all components to create training datasets.
This is the main entry point for using the Training Data Bot.
"""

import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from .ai import AIClient
from .core.config import settings
from .core.exceptions import ConfigurationError, TrainingDataBotError
from .core.logging import LogContext, get_logger
from .core.models import Dataset, Document, ProcessingJob, ProcessingStatus, TaskType, TrainingExample
from .decodo import DecodoClient
from .evaluation import QualityEvaluator
from .preprocessing import TextChunker, TextPreprocessor
from .sources import UnifiedLoader
from .storage import DatabaseManager, DatasetExporter
from .tasks import ClassificationGenerator, QAGenerator, SummarizationGenerator, TaskManager


class TrainingDataBot:
    """
    Main Training Data Bot class - The Factory Manager.

    Coordinates all components to transform documents into high-quality
    training datasets for LLM fine-tuning.

    Example:
        async with TrainingDataBot() as bot:
            # Load documents
            docs = await bot.load_documents(["paper.pdf", "https://example.com"])

            # Process into training data
            dataset = await bot.process_documents(docs, task_type="qa_generation")

            # Export
            await bot.export_dataset(dataset, "training_data.jsonl")
    """

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initialize the Training Data Bot.

        Args:
            config: Optional configuration overrides
        """
        self.logger = get_logger("training_data_bot")
        self.config = config or {}

        # Initialize components
        self._init_components()

        # State storage (Memory boxes)
        self.documents: Dict[UUID, Document] = {}
        self.datasets: Dict[UUID, Dataset] = {}
        self.jobs: Dict[UUID, ProcessingJob] = {}

        self.logger.info("Training Data Bot initialized successfully")

    def _init_components(self):
        """Initialize all bot components."""
        try:
            # Document loading
            self.loader = UnifiedLoader()

            # Optional services
            self.decodo_client = DecodoClient()
            self.db_manager = DatabaseManager()

            # AI and task management
            self.ai_client = AIClient(
                provider=self.config.get("ai_provider"),
                api_key=self.config.get("ai_api_key"),
                model=self.config.get("ai_model")
            )
            self.task_manager = TaskManager(ai_client=self.ai_client)

            # Text processing
            self.preprocessor = TextPreprocessor(
                aggressive=self.config.get("aggressive_cleaning", False)
            )
            self.chunker = TextChunker(
                chunk_size=self.config.get("chunk_size"),
                chunk_overlap=self.config.get("chunk_overlap")
            )

            # Quality and export
            self.evaluator = QualityEvaluator(
                threshold=self.config.get("quality_threshold")
            )
            self.exporter = DatasetExporter(
                include_metadata=self.config.get("include_metadata")
            )

            self.logger.debug("All components initialized")

        except Exception as e:
            raise ConfigurationError(
                "Failed to initialize bot components",
                details={"error": str(e)},
                original_error=e
            )

    # =========================================================================
    # MAIN SUPERPOWERS
    # =========================================================================

    async def load_documents(
        self,
        sources: Union[str, Path, List[Union[str, Path]]],
        max_workers: int = None
    ) -> List[Document]:
        """
        Load documents from various sources.

        Args:
            sources: Single source or list of sources (files, URLs, directories)
            max_workers: Maximum concurrent loads

        Returns:
            List of loaded Document objects

        Example:
            docs = await bot.load_documents([
                "textbook.pdf",
                "notes.txt",
                "https://wikipedia.org/wiki/AI"
            ])
        """
        # Normalize to list
        if not isinstance(sources, list):
            sources = [sources]

        max_workers = max_workers or settings.max_workers

        self.logger.info(f"Loading {len(sources)} document(s)")

        with LogContext(operation="load_documents"):
            # Check if any source is a directory
            expanded_sources = []
            for source in sources:
                source_path = Path(source) if not str(source).startswith('http') else None

                if source_path and source_path.is_dir():
                    # Load directory
                    dir_docs = await self.loader.load_directory(
                        source_path,
                        max_workers=max_workers
                    )
                    expanded_sources.extend([doc for doc in dir_docs])
                else:
                    expanded_sources.append(source)

            # Load individual sources
            if expanded_sources:
                documents = await self.loader.load_multiple(
                    [s for s in expanded_sources if not isinstance(s, Document)],
                    max_workers=max_workers
                )

                # Add pre-loaded documents from directories
                documents.extend([s for s in expanded_sources if isinstance(s, Document)])
            else:
                documents = []

            # Store in memory
            for doc in documents:
                self.documents[doc.id] = doc

            self.logger.info(f"Successfully loaded {len(documents)} documents")
            return documents

    async def process_documents(
        self,
        documents: List[Document],
        task_type: Union[TaskType, str] = TaskType.QA_GENERATION,
        task_config: Optional[Dict[str, Any]] = None,
        filter_quality: bool = True,
        on_progress: Optional[Any] = None
    ) -> Dataset:
        """
        Process documents into training dataset.

        Args:
            documents: Documents to process
            task_type: Type of training data to generate
            task_config: Task-specific configuration
            filter_quality: Filter low-quality examples
            on_progress: Optional callback (completed, total, latest_result)

        Returns:
            Dataset with training examples
        """
        # Normalize task type
        if isinstance(task_type, str):
            task_type = TaskType(task_type.lower())

        task_config = task_config or {}
        max_concurrent = task_config.get("max_concurrent", settings.max_concurrent_requests)

        self.logger.info(
            f"Processing {len(documents)} documents for {task_type.value} (concurrency={max_concurrent})"
        )

        with LogContext(operation="process_documents", task_type=task_type.value):
            # Step 1: Preprocess and chunk documents
            all_chunks = []
            for doc in documents:
                # Clean text
                cleaned_content = self.preprocessor.clean_for_training(doc.content)
                doc.content = cleaned_content

                # Chunk document
                chunks = self.chunker.chunk_document(doc)
                all_chunks.extend(chunks)

            self.logger.info(f"Created {len(all_chunks)} text chunks")

            # Step 2: Generate training examples based on task type
            if task_type == TaskType.QA_GENERATION:
                generator = QAGenerator(task_manager=self.task_manager)
                examples = await generator.generate_from_chunks(
                    all_chunks,
                    max_concurrent=max_concurrent,
                    on_progress=on_progress
                )

            elif task_type == TaskType.CLASSIFICATION:
                categories = task_config.get("categories", ["positive", "negative", "neutral"])
                generator = ClassificationGenerator(
                    categories=categories,
                    task_manager=self.task_manager
                )
                examples = await generator.generate_from_chunks(
                    all_chunks,
                    max_concurrent=max_concurrent,
                    on_progress=on_progress
                )

            elif task_type == TaskType.SUMMARIZATION:
                style = task_config.get("style", "concise")
                generator = SummarizationGenerator(
                    summary_style=style,
                    task_manager=self.task_manager
                )
                examples = await generator.generate_from_chunks(
                    all_chunks,
                    max_concurrent=max_concurrent,
                    on_progress=on_progress
                )

            else:
                raise TrainingDataBotError(
                    f"Unsupported task type: {task_type.value}",
                    details={"task_type": task_type.value}
                )

            self.logger.info(f"Generated {len(examples)} training examples")

            # Step 3: Create dataset
            dataset = Dataset(
                name=f"dataset_{task_type.value}",
                description=f"Training dataset for {task_type.value}",
                examples=examples,
                total_examples=len(examples)
            )

            # Step 4: Filter for quality (optional)
            if filter_quality:
                self.logger.info("Filtering dataset for quality...")
                dataset = await self.evaluator.filter_dataset(dataset)
                self.logger.info(f"After filtering: {len(dataset.examples)} examples")

            # Store dataset
            self.datasets[dataset.id] = dataset

            return dataset

    async def evaluate_dataset(
        self,
        dataset: Dataset
    ) -> Dict[str, Any]:
        """
        Evaluate dataset quality.

        Args:
            dataset: Dataset to evaluate

        Returns:
            Quality report dictionary

        Example:
            report = await bot.evaluate_dataset(dataset)
            print(f"Quality score: {report['overall_score']}")
        """
        self.logger.info(f"Evaluating dataset: {dataset.name}")

        report = await self.evaluator.evaluate_dataset(dataset)

        return {
            "overall_score": report.overall_score,
            "passed": report.passed,
            "metric_scores": report.metric_scores,
            "issues": report.issues,
            "warnings": report.warnings,
            "total_examples": len(dataset.examples)
        }

    async def export_dataset(
        self,
        dataset: Dataset,
        output_path: Union[str, Path],
        format: str = None,
        split: bool = False
    ) -> Union[Path, Dict[str, Path]]:
        """
        Export dataset to file(s).

        Args:
            dataset: Dataset to export
            output_path: Output file path or directory (if split=True)
            format: Export format (jsonl, json, csv)
            split: Split into train/val/test files

        Returns:
            Path to exported file, or dict of paths if split=True

        Example:
            # Single file
            path = await bot.export_dataset(dataset, "training.jsonl")

            # Split files
            paths = await bot.export_dataset(dataset, "output/", split=True)
        """
        self.logger.info(f"Exporting dataset: {dataset.name}")

        if split:
            return await self.exporter.export_split_dataset(
                dataset,
                output_path,
                format=format
            )
        else:
            return await self.exporter.export_dataset(
                dataset,
                output_path,
                format=format
            )

    # =========================================================================
    # CONVENIENCE METHODS
    # =========================================================================

    async def quick_process(
        self,
        source: Union[str, Path, List[Union[str, Path]]],
        output_path: Union[str, Path],
        task_type: str = "qa_generation",
        **kwargs
    ) -> Dataset:
        """
        One-line processing: load → process → export.

        Args:
            source: Source file(s), URL(s), or directory
            output_path: Output file path
            task_type: Task type
            **kwargs: Additional configuration

        Returns:
            Processed dataset

        Example:
            dataset = await bot.quick_process(
                source="documents/",
                output_path="training.jsonl",
                task_type="qa_generation"
            )
        """
        self.logger.info("Quick process started")

        # Load
        documents = await self.load_documents(source)

        # Process
        dataset = await self.process_documents(
            documents,
            task_type=task_type,
            task_config=kwargs
        )

        # Export
        await self.export_dataset(dataset, output_path)

        self.logger.info("Quick process complete")
        return dataset

    def get_statistics(self) -> Dict[str, Any]:
        """
        Get processing statistics.

        Returns:
            Dictionary with current statistics
        """
        return {
            "documents_loaded": len(self.documents),
            "datasets_created": len(self.datasets),
            "total_examples": sum(len(ds.examples) for ds in self.datasets.values()),
            "jobs_running": sum(
                1 for job in self.jobs.values()
                if job.status == ProcessingStatus.PROCESSING
            )
        }

    # =========================================================================
    # CONTEXT MANAGER & CLEANUP
    # =========================================================================

    async def cleanup(self):
        """Cleanup resources."""
        self.logger.info("Cleaning up resources...")

        if self.loader and hasattr(self.loader, "close"):
            await self.loader.close()

        if self.ai_client:
            await self.ai_client.close()

        if self.task_manager:
            await self.task_manager.close()

        if self.db_manager:
            await self.db_manager.close()

        if self.decodo_client:
            await self.decodo_client.close()

        self.logger.info("Cleanup complete")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.cleanup()

    def __repr__(self) -> str:
        """String representation."""
        return f"TrainingDataBot(docs={len(self.documents)}, datasets={len(self.datasets)})"
