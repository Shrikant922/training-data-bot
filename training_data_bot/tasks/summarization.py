"""
Summarization Generator - Text Summarization Data

Generates summarization training data from text chunks.
"""

from typing import Any, List, Optional
from uuid import uuid4

from ..core.logging import get_logger
from ..core.models import TaskTemplate, TaskType, TextChunk, TrainingExample
from .manager import TaskManager


class SummarizationGenerator:
    """
    Generates summarization training data from text.

    Creates training examples suitable for:
    - Text summarization models
    - Abstractive summarization
    - Extractive summarization
    - Key point extraction
    """

    def __init__(
        self,
        summary_style: str = "concise",
        task_manager: Optional[TaskManager] = None
    ):
        """
        Initialize the summarization generator.

        Args:
            summary_style: Style of summary ("concise", "detailed", "bullet_points")
            task_manager: TaskManager instance (creates one if not provided)

        Example:
            generator = SummarizationGenerator(summary_style="concise")
        """
        self.logger = get_logger("summarization_generator")
        self.summary_style = summary_style
        self.task_manager = task_manager or TaskManager()

        # Create template
        self.template = self._create_template()
        self.template_id = self.task_manager.register_template(self.template)

        self.logger.info(f"Summarization generator initialized (style={summary_style})")

    def _create_template(self) -> TaskTemplate:
        """Create summarization template based on style."""
        style_instructions = {
            "concise": "Create a brief, concise summary in 2-3 sentences that captures the main points.",
            "detailed": "Create a detailed summary that covers all key points and important details. Use 4-6 sentences.",
            "bullet_points": "Create a summary in bullet point format, listing the main points (3-5 bullets)."
        }

        instruction = style_instructions.get(
            self.summary_style,
            style_instructions["concise"]
        )

        prompt = f"""You are an expert at summarizing text.

Given the following text, {instruction}

The summary should:
1. Capture the core message and key information
2. Be clear and well-written
3. Maintain factual accuracy
4. Be significantly shorter than the original

Text:
{{text}}

Summary:"""

        return TaskTemplate(
            id=uuid4(),
            name=f"Summarization ({self.summary_style})",
            task_type=TaskType.SUMMARIZATION,
            description=f"Generate {self.summary_style} summaries from text",
            prompt_template=prompt,
            parameters={
                "temperature": 0.5,
                "max_tokens": 500,
                "style": self.summary_style
            }
        )

    async def generate_from_chunk(
        self,
        chunk: TextChunk
    ) -> Optional[TrainingExample]:
        """
        Generate summarization example from a text chunk.

        Args:
            chunk: Text chunk to summarize

        Returns:
            TrainingExample or None if generation fails

        Example:
            generator = SummarizationGenerator()
            example = await generator.generate_from_chunk(chunk)
        """
        self.logger.debug(f"Summarizing chunk {chunk.id}")

        # Execute task
        result = await self.task_manager.execute_task(self.template, chunk)

        # Parse the summary
        summary = self._parse_summary_output(result.output)

        if not summary:
            self.logger.warning(f"Failed to generate summary for chunk {chunk.id}")
            return None

        # Create training example
        # Input: the original text, Output: the summary
        example = TrainingExample(
            input_text=chunk.content,
            output_text=summary,
            task_type=TaskType.SUMMARIZATION,
            source_document_id=chunk.document_id,
            source_chunk_id=chunk.id,
            quality_scores=result.quality_scores,
            metadata={
                "style": self.summary_style,
                "compression_ratio": len(summary) / len(chunk.content)
            }
        )

        return example

    async def generate_from_chunks(
        self,
        chunks: List[TextChunk],
        max_concurrent: int = None,
        on_progress: Optional[Any] = None
    ) -> List[TrainingExample]:
        """
        Generate summarization examples from multiple chunks.

        Args:
            chunks: List of text chunks
            max_concurrent: Maximum concurrent summarizations
            on_progress: Optional progress callback

        Returns:
            List of TrainingExamples
        """
        self.logger.info(f"Summarizing {len(chunks)} chunks")

        # Execute batch
        results = await self.task_manager.execute_batch(
            self.template,
            chunks,
            max_concurrent=max_concurrent,
            on_progress=on_progress
        )

        # Parse all results — results[i] corresponds to chunks[i], None means chunk failed
        examples = []
        for chunk, result in zip(chunks, results):
            if result is None:
                continue  # This chunk failed, skip it

            summary = self._parse_summary_output(result.output)

            if summary:
                example = TrainingExample(
                    input_text=chunk.content,
                    output_text=summary,
                    task_type=TaskType.SUMMARIZATION,
                    source_document_id=chunk.document_id,
                    source_chunk_id=chunk.id,
                    quality_scores=result.quality_scores,
                    metadata={
                        "style": self.summary_style,
                        "compression_ratio": len(summary) / len(chunk.content)
                    }
                )
                examples.append(example)

        self.logger.info(f"Generated {len(examples)} summarization examples")
        return examples

    def _parse_summary_output(self, output: str) -> Optional[str]:
        """
        Parse the AI output to extract the summary.

        Args:
            output: Raw AI output

        Returns:
            Cleaned summary text or None
        """
        # Remove "Summary:" prefix if present
        summary = output.strip()

        if summary.lower().startswith("summary:"):
            summary = summary[8:].strip()

        # Validate summary is not empty
        if not summary or len(summary) < 10:
            return None

        return summary

    def set_custom_template(self, template: TaskTemplate) -> None:
        """
        Use a custom task template.

        Args:
            template: Custom TaskTemplate for summarization
        """
        self.template = template
        self.template_id = self.task_manager.register_template(template)
        self.logger.info(f"Using custom template: {template.name}")

    def __repr__(self) -> str:
        """String representation."""
        return f"SummarizationGenerator(style={self.summary_style})"
