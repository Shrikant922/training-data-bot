"""
Task Manager - Task Orchestration

Manages task templates and coordinates task execution across text chunks.
Acts as the central coordinator for all training data generation tasks.
"""

import asyncio
from typing import Any, Callable, Dict, List, Optional
from uuid import UUID, uuid4

from ..ai.client import AIClient
from ..core.config import settings
from ..core.exceptions import TaskGenerationError
from ..core.logging import LogContext, get_logger
from ..core.models import TaskResult, TaskTemplate, TaskType, TextChunk


class TaskManager:
    """
    Manages task templates and orchestrates task execution.

    Coordinates between:
    - Task templates (what to do)
    - Text chunks (what to process)
    - AI client (how to process)
    """

    def __init__(self, ai_client: Optional[AIClient] = None):
        """
        Initialize the task manager.

        Args:
            ai_client: AI client instance (creates one if not provided)
        """
        self.logger = get_logger("task_manager")
        self.ai_client = ai_client or AIClient()

        # Storage for task templates
        self.templates: Dict[UUID, TaskTemplate] = {}

        self.logger.info("Task manager initialized")

    def register_template(self, template: TaskTemplate) -> UUID:
        """
        Register a task template.

        Args:
            template: Task template to register

        Returns:
            Template ID

        Example:
            manager = TaskManager()
            template = TaskTemplate(
                name="Question Generation",
                task_type=TaskType.QA_GENERATION,
                description="Generate questions from text",
                prompt_template="Generate 3 questions about: {text}"
            )
            template_id = manager.register_template(template)
        """
        self.templates[template.id] = template
        self.logger.info(f"Registered template: {template.name} ({template.task_type.value})")
        return template.id

    def get_template(self, template_id: UUID) -> Optional[TaskTemplate]:
        """
        Get a registered template by ID.

        Args:
            template_id: Template ID

        Returns:
            TaskTemplate or None if not found
        """
        return self.templates.get(template_id)

    def list_templates(self, task_type: Optional[TaskType] = None) -> List[TaskTemplate]:
        """
        List registered templates, optionally filtered by type.

        Args:
            task_type: Filter by task type (optional)

        Returns:
            List of templates
        """
        templates = list(self.templates.values())

        if task_type:
            templates = [t for t in templates if t.task_type == task_type]

        return templates

    async def execute_task(
        self,
        template: TaskTemplate,
        chunk: TextChunk,
        **kwargs
    ) -> TaskResult:
        """
        Execute a task on a single text chunk.

        Args:
            template: Task template to use
            chunk: Text chunk to process
            **kwargs: Additional parameters

        Returns:
            TaskResult with generated output

        Example:
            result = await manager.execute_task(template, chunk)
        """
        with LogContext(
            task_type=template.task_type.value,
            chunk_id=str(chunk.id),
            template_id=str(template.id)
        ):
            self.logger.debug(f"Executing task: {template.name}")

            import time
            start_time = time.time()

            try:
                # Format the prompt with chunk content
                prompt = self._format_prompt(template, chunk, **kwargs)

                # Generate using AI client
                output = await self.ai_client.generate(
                    prompt=prompt,
                    temperature=template.parameters.get("temperature"),
                    max_tokens=template.parameters.get("max_tokens"),
                )

                # Calculate processing time
                processing_time = time.time() - start_time

                # Create result
                result = TaskResult(
                    task_id=template.id,
                    input_chunk_id=chunk.id,
                    output=output,
                    confidence=1.0,  # Can be improved with confidence scoring
                    quality_scores={},  # Can be populated by evaluator
                    processing_time=processing_time
                )

                self.logger.debug(f"Task completed in {processing_time:.2f}s")
                return result

            except Exception as e:
                raise TaskGenerationError(
                    f"Task execution failed: {template.name}",
                    details={
                        "template_id": str(template.id),
                        "chunk_id": str(chunk.id),
                        "task_type": template.task_type.value
                    },
                    original_error=e
                )

    async def execute_batch(
        self,
        template: TaskTemplate,
        chunks: List[TextChunk],
        max_concurrent: int = None,
        on_progress: Optional[Any] = None,
        **kwargs
    ) -> List[TaskResult]:
        """
        Execute a task on multiple chunks in parallel.

        Args:
            template: Task template to use
            chunks: List of text chunks to process
            max_concurrent: Maximum concurrent executions
            on_progress: Optional callback (completed, total, result)
            **kwargs: Additional parameters

        Returns:
            List of TaskResults
        """
        max_concurrent = max_concurrent or settings.max_concurrent_requests
        total_chunks = len(chunks)
        completed_chunks = 0
        progress_lock = asyncio.Lock()

        self.logger.info(
            f"Batch executing task '{template.name}' on {total_chunks} chunks "
            f"(max_concurrent={max_concurrent})"
        )

        semaphore = asyncio.Semaphore(max_concurrent)

        async def execute_with_semaphore(chunk):
            nonlocal completed_chunks
            async with semaphore:
                try:
                    result = await self.execute_task(template, chunk, **kwargs)
                except Exception as e:
                    self.logger.error(f"Chunk {chunk.id} failed: {e}")
                    result = None  # Preserve position — do NOT filter here

                async with progress_lock:
                    completed_chunks += 1
                    current_completed = completed_chunks

                if on_progress:
                    try:
                        if asyncio.iscoroutinefunction(on_progress):
                            await on_progress(current_completed, total_chunks, result)
                        else:
                            on_progress(current_completed, total_chunks, result)
                    except Exception as prog_err:
                        self.logger.debug(f"on_progress callback error: {prog_err}")

                return result

        results = await asyncio.gather(
            *[execute_with_semaphore(chunk) for chunk in chunks]
        )

        # Results list is same length as chunks — None means that chunk failed
        success_count = sum(1 for r in results if r is not None)
        self.logger.info(
            f"Batch complete: {success_count}/{total_chunks} succeeded"
        )

        return list(results)  # Preserve all positions (None = failed chunk)

    def _format_prompt(
        self,
        template: TaskTemplate,
        chunk: TextChunk,
        **kwargs
    ) -> str:
        """
        Format the prompt template with chunk content and parameters.

        Args:
            template: Task template
            chunk: Text chunk
            **kwargs: Additional format parameters

        Returns:
            Formatted prompt string
        """
        # Combine template parameters with additional kwargs
        format_params = {
            "text": chunk.content,
            "chunk_index": chunk.chunk_index,
            **template.parameters,
            **kwargs
        }

        try:
            return template.prompt_template.format(**format_params)
        except KeyError as e:
            raise TaskGenerationError(
                f"Missing parameter in prompt template: {e}",
                details={
                    "template_id": str(template.id),
                    "missing_key": str(e)
                }
            )

    async def close(self):
        """Close the task manager and cleanup resources."""
        if self.ai_client:
            await self.ai_client.close()
        self.logger.info("Task manager closed")

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()

    def __repr__(self) -> str:
        """String representation."""
        return f"TaskManager(templates={len(self.templates)})"
