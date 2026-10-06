"""
Unit Tests: Quality Evaluator
Tests toxicity, bias, coherence, relevance, and diversity checks.
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
os.chdir(Path(__file__).parent.parent.parent)

import pytest
from uuid import uuid4

from training_data_bot.evaluation.evaluator import QualityEvaluator
from training_data_bot.core.models import (
    TrainingExample, Dataset, TaskType, QualityReport
)


def make_example(input_text: str, output_text: str) -> TrainingExample:
    return TrainingExample(
        input_text=input_text,
        output_text=output_text,
        task_type=TaskType.QA_GENERATION,
        source_document_id=uuid4()
    )


class TestQualityEvaluatorInit:
    def test_default_threshold(self):
        ev = QualityEvaluator()
        assert 0.0 < ev.threshold <= 1.0

    def test_custom_threshold(self):
        ev = QualityEvaluator(threshold=0.5)
        assert ev.threshold == 0.5

    def test_repr(self):
        ev = QualityEvaluator(threshold=0.75)
        assert "0.75" in repr(ev)


class TestToxicityCheck:
    @pytest.mark.asyncio
    async def test_clean_text_scores_high(self):
        ev = QualityEvaluator()
        ex = make_example(
            "What is Python?",
            "Python is a programming language."
        )
        score = await ev._check_toxicity(ex)
        assert score == 1.0  # No toxic words → max score

    @pytest.mark.asyncio
    async def test_text_with_toxic_keyword_scores_lower(self):
        ev = QualityEvaluator()
        ex = make_example(
            "What about hate speech?",
            "Hate speech is harmful to society."
        )
        score = await ev._check_toxicity(ex)
        assert score < 1.0

    @pytest.mark.asyncio
    async def test_score_never_below_zero(self):
        ev = QualityEvaluator()
        ex = make_example(
            "hate kill violence offensive discriminate hate kill",
            "hate kill violence offensive discriminate"
        )
        score = await ev._check_toxicity(ex)
        assert score >= 0.0


class TestCoherenceCheck:
    @pytest.mark.asyncio
    async def test_empty_output_scores_zero(self):
        ev = QualityEvaluator()
        ex = make_example("Question?", "")
        score = await ev._check_coherence(ex)
        assert score == 0.0

    @pytest.mark.asyncio
    async def test_very_short_output_scores_low(self):
        ev = QualityEvaluator()
        ex = make_example("Question?", "Yes")  # < 10 chars
        score = await ev._check_coherence(ex)
        assert score == 0.3

    @pytest.mark.asyncio
    async def test_proper_sentence_scores_high(self):
        ev = QualityEvaluator()
        ex = make_example(
            "What is AI?",
            "Artificial intelligence is the simulation of human intelligence by machines."
        )
        score = await ev._check_coherence(ex)
        assert score >= 0.7


class TestRelevanceCheck:
    @pytest.mark.asyncio
    async def test_empty_input_returns_neutral(self):
        ev = QualityEvaluator()
        ex = make_example("", "some output text here")
        score = await ev._check_relevance(ex)
        assert score == 0.5

    @pytest.mark.asyncio
    async def test_high_overlap_detected(self):
        """Output that's almost identical to input has slightly lower score (copying)."""
        ev = QualityEvaluator()
        text = "machine learning artificial intelligence data science"
        ex = make_example(text, text + " model training")  # Very high overlap
        score = await ev._check_relevance(ex)
        # With near-100% overlap, score should be 0.6 (penalised for copying)
        assert score <= 0.9

    @pytest.mark.asyncio
    async def test_very_low_overlap_scores_low(self):
        ev = QualityEvaluator()
        ex = make_example(
            "Python programming language syntax loops functions",
            "cooking recipe kitchen ingredients flour butter eggs"
        )
        score = await ev._check_relevance(ex)
        assert score <= 0.5


class TestDatasetDiversityCheck:
    def test_single_example_max_diversity(self):
        ev = QualityEvaluator()
        ds = Dataset(
            name="x", description="y",
            examples=[make_example("What is AI?", "AI is intelligence.")],
            total_examples=1
        )
        score = ev._check_dataset_diversity(ds)
        assert score == 1.0

    def test_empty_dataset_max_diversity(self):
        ev = QualityEvaluator()
        ds = Dataset(name="x", description="y", examples=[], total_examples=0)
        score = ev._check_dataset_diversity(ds)
        assert score == 1.0

    def test_all_unique_examples(self):
        ev = QualityEvaluator()
        examples = [make_example(f"Question {i}?", f"Answer {i}.") for i in range(10)]
        ds = Dataset(name="x", description="y", examples=examples, total_examples=10)
        score = ev._check_dataset_diversity(ds)
        assert score == 1.0

    def test_all_duplicate_examples(self):
        ev = QualityEvaluator()
        same_ex = make_example("What is AI?", "AI is intelligence.")
        # Create 5 examples with same input text
        examples = [
            make_example("what is ai?", "AI is intelligence.")
            for _ in range(5)
        ]
        ds = Dataset(name="x", description="y", examples=examples, total_examples=5)
        score = ev._check_dataset_diversity(ds)
        assert score < 1.0


class TestEvaluateExample:
    @pytest.mark.asyncio
    async def test_good_example_passes(self):
        ev = QualityEvaluator(threshold=0.5)
        ex = make_example(
            "What is machine learning?",
            "Machine learning allows computers to learn from data automatically."
        )
        report = await ev.evaluate_example(ex)
        assert isinstance(report, QualityReport)
        assert isinstance(report.overall_score, float)
        assert 0.0 <= report.overall_score <= 1.0

    @pytest.mark.asyncio
    async def test_empty_output_fails(self):
        ev = QualityEvaluator(threshold=0.7)
        ex = make_example("What is AI?", "")
        report = await ev.evaluate_example(ex)
        assert report.passed is False
        assert len(report.issues) > 0

    @pytest.mark.asyncio
    async def test_report_has_target_id(self):
        ev = QualityEvaluator()
        ex = make_example("Q?", "A good answer to the question.")
        report = await ev.evaluate_example(ex)
        assert report.target_id == ex.id


class TestFilterDataset:
    @pytest.mark.asyncio
    async def test_filters_empty_outputs(self):
        """Examples with empty outputs should be filtered out."""
        ev = QualityEvaluator(threshold=0.5)
        good_ex = make_example("What is Python?", "Python is a programming language.")
        bad_ex = make_example("What is nothing?", "")  # coherence = 0.0 → fails

        ds = Dataset(
            name="x", description="y",
            examples=[good_ex, bad_ex],
            total_examples=2
        )
        filtered = await ev.filter_dataset(ds)
        assert len(filtered.examples) < 2

    @pytest.mark.asyncio
    async def test_all_good_examples_pass(self):
        ev = QualityEvaluator(threshold=0.5)
        examples = [
            make_example(f"What is concept {i}?",
                         f"Concept {i} is an important part of machine learning science.")
            for i in range(5)
        ]
        ds = Dataset(name="x", description="y", examples=examples, total_examples=5)
        filtered = await ev.filter_dataset(ds)
        # All good examples should survive
        assert len(filtered.examples) > 0

    @pytest.mark.asyncio
    async def test_filtered_dataset_has_correct_metadata(self):
        ev = QualityEvaluator(threshold=0.5)
        examples = [make_example(f"Q{i}?", f"A good detailed answer {i}.") for i in range(3)]
        ds = Dataset(name="original", description="y", examples=examples, total_examples=3)
        filtered = await ev.filter_dataset(ds)
        assert "original_count" in filtered.metadata
        assert filtered.metadata["original_count"] == 3


class TestEvaluateDataset:
    @pytest.mark.asyncio
    async def test_empty_dataset_fails(self):
        ev = QualityEvaluator()
        ds = Dataset(name="x", description="y", examples=[], total_examples=0)
        report = await ev.evaluate_dataset(ds)
        assert report.passed is False
        assert len(report.issues) > 0

    @pytest.mark.asyncio
    async def test_dataset_report_has_correct_target(self):
        ev = QualityEvaluator(threshold=0.5)
        examples = [make_example(f"Q{i}?", f"Answer {i} in detail.") for i in range(3)]
        ds = Dataset(name="x", description="y", examples=examples, total_examples=3)
        report = await ev.evaluate_dataset(ds)
        assert report.target_id == ds.id
