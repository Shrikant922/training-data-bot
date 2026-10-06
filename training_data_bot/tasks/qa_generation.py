"""
QA Generator - Question-Answer Pair Generation

Generates question-answer pairs from text chunks for Q&A training data.
"""

from typing import Any, Dict, List, Optional
from uuid import uuid4

from ..core.logging import get_logger
from ..core.models import TaskTemplate, TaskType, TextChunk, TrainingExample
from .manager import TaskManager


class QAGenerator:
    """
    Generates question-answer pairs from text.

    Creates training examples suitable for:
    - Question answering models
    - Conversational AI
    - Information retrieval tasks
    """

    def __init__(self, task_manager: Optional[TaskManager] = None):
        """
        Initialize the QA generator.

        Args:
            task_manager: TaskManager instance (creates one if not provided)
        """
        self.logger = get_logger("qa_generator")
        self.task_manager = task_manager or TaskManager()

        # Create default template
        self.template = self._create_default_template()
        self.template_id = self.task_manager.register_template(self.template)

        self.logger.info("QA generator initialized")

    def _create_default_template(self) -> TaskTemplate:
        """Create default Q&A generation template."""
        prompt = """You are an expert at creating high-quality question-answer pairs from text.

Given the following text, generate 3-5 relevant questions and their answers.

Rules:
1. Questions should be clear and specific
2. Answers should be directly supported by the text
3. Vary question types (what, why, how, when, etc.)
4. Avoid yes/no questions when possible
5. Make questions challenging but answerable

Text:
{text}

Format your response as:
Q1: [Question]
A1: [Answer]

Q2: [Question]
A2: [Answer]

... and so on."""

        return TaskTemplate(
            id=uuid4(),
            name="QA Generation",
            task_type=TaskType.QA_GENERATION,
            description="Generate question-answer pairs from text",
            prompt_template=prompt,
            parameters={
                "temperature": 0.7,
                "max_tokens": 1000,
            }
        )

    async def generate_from_chunk(
        self,
        chunk: TextChunk,
        num_questions: int = 3
    ) -> List[TrainingExample]:
        """
        Generate Q&A pairs from a single text chunk.

        Args:
            chunk: Text chunk to process
            num_questions: Target number of questions to generate

        Returns:
            List of TrainingExample objects

        Example:
            generator = QAGenerator()
            examples = await generator.generate_from_chunk(chunk)
        """
        self.logger.debug(f"Generating Q&A from chunk {chunk.id}")

        # Execute task
        result = await self.task_manager.execute_task(
            self.template,
            chunk,
            num_questions=num_questions
        )

        # Parse the output into Q&A pairs
        qa_pairs = self._parse_qa_output(result.output)

        # Convert to training examples
        examples = []
        for question, answer in qa_pairs:
            example = TrainingExample(
                input_text=question,
                output_text=answer,
                task_type=TaskType.QA_GENERATION,
                source_document_id=chunk.document_id,
                source_chunk_id=chunk.id,
                quality_scores=result.quality_scores
            )
            examples.append(example)

        self.logger.info(f"Generated {len(examples)} Q&A pairs from chunk")
        return examples

    async def generate_from_chunks(
        self,
        chunks: List[TextChunk],
        num_questions: int = 3,
        max_concurrent: int = None,
        on_progress: Optional[Any] = None
    ) -> List[TrainingExample]:
        """
        Generate Q&A pairs from multiple chunks.

        Args:
            chunks: List of text chunks
            num_questions: Target questions per chunk
            max_concurrent: Maximum concurrent generations
            on_progress: Optional progress callback

        Returns:
            List of all generated TrainingExamples
        """
        self.logger.info(f"Generating Q&A from {len(chunks)} chunks")

        # Execute batch
        results = await self.task_manager.execute_batch(
            self.template,
            chunks,
            max_concurrent=max_concurrent,
            on_progress=on_progress,
            num_questions=num_questions
        )

        # Parse all results — results[i] corresponds to chunks[i], None means chunk failed
        all_examples = []
        for chunk, result in zip(chunks, results):
            if result is None:
                continue  # This chunk failed, skip it

            qa_pairs = self._parse_qa_output(result.output)

            for question, answer in qa_pairs:
                example = TrainingExample(
                    input_text=question,
                    output_text=answer,
                    task_type=TaskType.QA_GENERATION,
                    source_document_id=chunk.document_id,
                    source_chunk_id=chunk.id,
                    quality_scores=result.quality_scores
                )
                all_examples.append(example)

        self.logger.info(f"Generated {len(all_examples)} total Q&A pairs")
        return all_examples

    def _parse_qa_output(self, output: str) -> List[tuple[str, str]]:
        """
        Parse the AI output into question-answer pairs.

        Args:
            output: Raw AI output

        Returns:
            List of (question, answer) tuples
        """
        qa_pairs = []
        lines = output.strip().split('\n')

        current_question = None
        current_answer = None

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # Check for question
            if line.startswith('Q') and ':' in line:
                # Save previous pair if exists
                if current_question and current_answer:
                    qa_pairs.append((current_question, current_answer))

                # Start new question
                current_question = line.split(':', 1)[1].strip()
                current_answer = None

            # Check for answer
            elif line.startswith('A') and ':' in line:
                current_answer = line.split(':', 1)[1].strip()

            # Continuation of previous line
            elif current_answer is not None:
                current_answer += ' ' + line
            elif current_question is not None:
                current_question += ' ' + line

        # Save last pair
        if current_question and current_answer:
            qa_pairs.append((current_question, current_answer))

        return qa_pairs

    def set_custom_template(self, template: TaskTemplate) -> None:
        """
        Use a custom task template instead of the default.

        Args:
            template: Custom TaskTemplate for Q&A generation
        """
        self.template = template
        self.template_id = self.task_manager.register_template(template)
        self.logger.info(f"Using custom template: {template.name}")

    def __repr__(self) -> str:
        """String representation."""
        return "QAGenerator()"
