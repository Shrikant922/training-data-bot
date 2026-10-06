"""
Classification Generator - Text Classification Data

Generates classification training data from text chunks.
"""

from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.logging import get_logger
from ..core.models import TaskTemplate, TaskType, TextChunk, TrainingExample
from .manager import TaskManager


class ClassificationGenerator:
    """
    Generates classification training data from text.

    Creates training examples suitable for:
    - Text classification
    - Sentiment analysis
    - Topic categorization
    - Intent detection
    """

    def __init__(
        self,
        categories: List[str],
        task_manager: Optional[TaskManager] = None
    ):
        """
        Initialize the classification generator.

        Args:
            categories: List of classification categories/labels
            task_manager: TaskManager instance (creates one if not provided)

        Example:
            generator = ClassificationGenerator(
                categories=["positive", "negative", "neutral"]
            )
        """
        self.logger = get_logger("classification_generator")
        self.categories = categories
        self.task_manager = task_manager or TaskManager()

        # Create template
        self.template = self._create_template()
        self.template_id = self.task_manager.register_template(self.template)

        self.logger.info(
            f"Classification generator initialized with {len(categories)} categories"
        )

    def _create_template(self) -> TaskTemplate:
        """Create classification template."""
        categories_str = ", ".join(self.categories)

        prompt = f"""You are an expert at text classification.

Given the following text, classify it into one of these categories: {categories_str}

Provide:
1. The most appropriate category
2. A brief explanation (1-2 sentences) of why you chose that category
3. Confidence level (high/medium/low)

Text:
{{text}}

Format your response as:
Category: [chosen category]
Explanation: [brief explanation]
Confidence: [high/medium/low]"""

        return TaskTemplate(
            id=uuid4(),
            name="Text Classification",
            task_type=TaskType.CLASSIFICATION,
            description=f"Classify text into categories: {categories_str}",
            prompt_template=prompt,
            parameters={
                "temperature": 0.3,  # Lower temperature for more consistent classification
                "max_tokens": 500,
                "categories": self.categories
            }
        )

    async def generate_from_chunk(
        self,
        chunk: TextChunk
    ) -> Optional[TrainingExample]:
        """
        Generate classification example from a text chunk.

        Args:
            chunk: Text chunk to classify

        Returns:
            TrainingExample or None if generation fails
        """
        self.logger.debug(f"Classifying chunk {chunk.id}")

        # Execute task
        result = await self.task_manager.execute_task(self.template, chunk)

        # Parse the output
        classification = self._parse_classification_output(result.output)

        if not classification:
            self.logger.warning(f"Failed to parse classification for chunk {chunk.id}")
            return None

        # Create training example
        # Input: the text, Output: the category
        example = TrainingExample(
            input_text=chunk.content,
            output_text=classification["category"],
            task_type=TaskType.CLASSIFICATION,
            source_document_id=chunk.document_id,
            source_chunk_id=chunk.id,
            quality_scores=result.quality_scores,
            metadata={
                "explanation": classification.get("explanation"),
                "confidence": classification.get("confidence")
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
        Generate classification examples from multiple chunks.

        Args:
            chunks: List of text chunks
            max_concurrent: Maximum concurrent classifications
            on_progress: Optional progress callback

        Returns:
            List of TrainingExamples
        """
        self.logger.info(f"Classifying {len(chunks)} chunks")

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

            classification = self._parse_classification_output(result.output)

            if classification:
                example = TrainingExample(
                    input_text=chunk.content,
                    output_text=classification["category"],
                    task_type=TaskType.CLASSIFICATION,
                    source_document_id=chunk.document_id,
                    source_chunk_id=chunk.id,
                    quality_scores=result.quality_scores,
                    metadata={
                        "explanation": classification.get("explanation"),
                        "confidence": classification.get("confidence")
                    }
                )
                examples.append(example)

        self.logger.info(f"Generated {len(examples)} classification examples")
        return examples

    def _parse_classification_output(self, output: str) -> Optional[Dict[str, str]]:
        """
        Parse the AI output into classification data.

        Args:
            output: Raw AI output

        Returns:
            Dictionary with category, explanation, confidence or None
        """
        result = {}
        lines = output.strip().split('\n')

        for line in lines:
            line = line.strip()
            if ':' not in line:
                continue

            key, value = line.split(':', 1)
            key = key.strip().lower()
            value = value.strip()

            if key == 'category':
                result['category'] = value
            elif key == 'explanation':
                result['explanation'] = value
            elif key == 'confidence':
                result['confidence'] = value

        # Validate that we got a category
        if 'category' not in result:
            return None

        # Validate category is in allowed list
        if result['category'] not in self.categories:
            self.logger.warning(
                f"Invalid category '{result['category']}', expected one of {self.categories}"
            )
            return None

        return result

    def set_custom_template(self, template: TaskTemplate) -> None:
        """
        Use a custom task template.

        Args:
            template: Custom TaskTemplate for classification
        """
        self.template = template
        self.template_id = self.task_manager.register_template(template)
        self.logger.info(f"Using custom template: {template.name}")

    def __repr__(self) -> str:
        """String representation."""
        return f"ClassificationGenerator(categories={self.categories})"
