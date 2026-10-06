"""
Quality Evaluator - Training Data Quality Assessment

Evaluates the quality of generated training data using multiple metrics.
"""

import asyncio
from typing import Dict, List, Optional
from uuid import UUID

from ..core.config import settings
from ..core.exceptions import EvaluationError, ThresholdError
from ..core.logging import get_logger
from ..core.models import QualityMetric, QualityReport, TrainingExample, Dataset, TaskType


class QualityEvaluator:
    """
    Evaluates training data quality across multiple dimensions.

    Checks for:
    - Toxicity
    - Bias
    - Diversity
    - Coherence
    - Relevance
    """

    def __init__(self, threshold: float = None):
        """
        Initialize the quality evaluator.

        Args:
            threshold: Minimum quality score to pass (0.0 to 1.0)
        """
        self.logger = get_logger("quality_evaluator")
        self.threshold = threshold or settings.quality_threshold

        # Track which checks are enabled
        self.enabled_checks = {
            QualityMetric.TOXICITY: settings.enable_toxicity_check,
            QualityMetric.BIAS: settings.enable_bias_check,
            QualityMetric.DIVERSITY: settings.enable_diversity_check,
            QualityMetric.COHERENCE: settings.enable_coherence_check,
            QualityMetric.RELEVANCE: settings.enable_relevance_check,
        }

        enabled_count = sum(1 for v in self.enabled_checks.values() if v)
        self.logger.info(
            f"Quality evaluator initialized (threshold={threshold}, "
            f"enabled_checks={enabled_count})"
        )

    async def evaluate_example(
        self,
        example: TrainingExample
    ) -> QualityReport:
        """
        Evaluate a single training example.

        Args:
            example: TrainingExample to evaluate

        Returns:
            QualityReport with scores and pass/fail status

        Example:
            evaluator = QualityEvaluator(threshold=0.7)
            report = await evaluator.evaluate_example(example)
        """
        self.logger.debug(f"Evaluating example {example.id}")

        metric_scores = {}
        issues = []
        warnings = []

        # Run each enabled check
        if self.enabled_checks[QualityMetric.TOXICITY]:
            score = await self._check_toxicity(example)
            metric_scores[QualityMetric.TOXICITY.value] = score
            if score < 0.5:
                issues.append(f"High toxicity detected (score: {score:.2f})")

        if self.enabled_checks[QualityMetric.BIAS]:
            score = await self._check_bias(example)
            metric_scores[QualityMetric.BIAS.value] = score
            if score < 0.6:
                warnings.append(f"Potential bias detected (score: {score:.2f})")

        if self.enabled_checks[QualityMetric.COHERENCE]:
            score = await self._check_coherence(example)
            metric_scores[QualityMetric.COHERENCE.value] = score
            if score < 0.5:
                issues.append(f"Low coherence (score: {score:.2f})")

        if self.enabled_checks[QualityMetric.RELEVANCE]:
            score = await self._check_relevance(example)
            metric_scores[QualityMetric.RELEVANCE.value] = score
            if score < 0.5:
                issues.append(f"Low relevance (score: {score:.2f})")

        # Calculate overall score (average of all metrics)
        if metric_scores:
            overall_score = sum(metric_scores.values()) / len(metric_scores)
        else:
            overall_score = 1.0  # No checks enabled, assume pass

        # Determine if passed
        passed = overall_score >= self.threshold and len(issues) == 0

        # Create report
        report = QualityReport(
            target_id=example.id,
            overall_score=overall_score,
            passed=passed,
            metric_scores=metric_scores,
            issues=issues,
            warnings=warnings
        )

        return report

    async def evaluate_dataset(
        self,
        dataset: Dataset
    ) -> QualityReport:
        """
        Evaluate an entire dataset.

        Args:
            dataset: Dataset to evaluate

        Returns:
            QualityReport for the dataset
        """
        self.logger.info(f"Evaluating dataset: {dataset.name} ({len(dataset.examples)} examples)")

        # Evaluate all examples concurrently in parallel
        if dataset.examples:
            example_reports = await asyncio.gather(
                *[self.evaluate_example(example) for example in dataset.examples]
            )
        else:
            example_reports = []

        # Calculate aggregate metrics
        metric_scores = {}
        issues = []
        warnings = []

        if example_reports:
            # Average each metric across all examples
            all_metrics = set()
            for report in example_reports:
                all_metrics.update(report.metric_scores.keys())

            for metric in all_metrics:
                scores = [
                    r.metric_scores.get(metric, 0)
                    for r in example_reports
                    if metric in r.metric_scores
                ]
                if scores:
                    metric_scores[metric] = sum(scores) / len(scores)

            # Overall score
            overall_score = sum(metric_scores.values()) / len(metric_scores) if metric_scores else 1.0

            # Count issues and warnings
            failed_count = sum(1 for r in example_reports if not r.passed)
            if failed_count > 0:
                issues.append(f"{failed_count} examples failed quality checks")

            # Check diversity
            if self.enabled_checks[QualityMetric.DIVERSITY]:
                diversity_score = self._check_dataset_diversity(dataset)
                metric_scores[QualityMetric.DIVERSITY.value] = diversity_score
                if diversity_score < 0.5:
                    warnings.append(f"Low dataset diversity (score: {diversity_score:.2f})")

        else:
            overall_score = 0.0
            issues.append("No examples to evaluate")

        # Dataset passes if overall score meets threshold and no critical issues
        passed = overall_score >= self.threshold and len(issues) == 0

        # Create report
        report = QualityReport(
            target_id=dataset.id,
            overall_score=overall_score,
            passed=passed,
            metric_scores=metric_scores,
            issues=issues,
            warnings=warnings,
            metadata={
                "total_examples": len(dataset.examples),
                "failed_examples": sum(1 for r in example_reports if not r.passed)
            }
        )

        self.logger.info(
            f"Dataset evaluation complete: score={overall_score:.2f}, passed={passed}"
        )

        return report

    async def filter_dataset(
        self,
        dataset: Dataset,
        min_score: Optional[float] = None
    ) -> Dataset:
        """
        Filter dataset to only include high-quality examples.

        Args:
            dataset: Dataset to filter
            min_score: Minimum quality score (uses threshold if not provided)

        Returns:
            New Dataset with only passing examples
        """
        min_score = min_score or self.threshold

        self.logger.info(f"Filtering dataset with min_score={min_score}")

        # Evaluate all examples in parallel
        filtered_examples = []
        if dataset.examples:
            reports = await asyncio.gather(
                *[self.evaluate_example(example) for example in dataset.examples]
            )
            for example, report in zip(dataset.examples, reports):
                if report.passed and report.overall_score >= min_score:
                    # Update example quality scores
                    example.quality_scores = report.metric_scores
                    filtered_examples.append(example)

        # Create filtered dataset
        filtered_dataset = Dataset(
            name=f"{dataset.name} (filtered)",
            description=f"{dataset.description} - Filtered for quality (min_score={min_score})",
            examples=filtered_examples,
            total_examples=len(filtered_examples),
            train_split=dataset.train_split,
            validation_split=dataset.validation_split,
            test_split=dataset.test_split,
            metadata={
                **dataset.metadata,
                "original_count": len(dataset.examples),
                "filtered_count": len(filtered_examples),
                "filter_threshold": min_score
            }
        )

        self.logger.info(
            f"Filtered dataset: {len(dataset.examples)} → {len(filtered_examples)} examples"
        )

        return filtered_dataset

    # -------------------------------------------------------------------------
    # Individual Quality Checks (simplified versions - can be enhanced)
    # -------------------------------------------------------------------------

    async def _check_toxicity(self, example: TrainingExample) -> float:
        """Check for toxic content. Returns 1.0 (clean) to 0.0 (toxic)."""
        # Simplified: check for common toxic patterns
        text = (example.input_text + " " + example.output_text).lower()

        toxic_keywords = [
            "hate", "kill", "violence", "offensive", "discriminate"
        ]

        toxic_count = sum(1 for word in toxic_keywords if word in text)

        # Score: 1.0 if no toxic words, decreases with count
        score = max(0.0, 1.0 - (toxic_count * 0.2))

        return score

    async def _check_bias(self, example: TrainingExample) -> float:
        """Check for biased content. Returns 1.0 (unbiased) to 0.0 (biased)."""
        # Simplified: check for stereotypical language
        # In production, use proper bias detection models

        return 0.9  # Placeholder - assume mostly unbiased

    async def _check_coherence(self, example: TrainingExample) -> float:
        """Check if output is coherent with input."""
        # Simplified: check basic properties
        output = example.output_text.strip()

        # Check if output is not empty
        if not output:
            return 0.0

        # For classification, output is simply a category label (e.g. "technical")
        if example.task_type == TaskType.CLASSIFICATION:
            return 1.0

        # Check if output has reasonable length
        if len(output) < 10:
            return 0.3

        # Check if output has proper sentence structure
        if not output[0].isupper() or output[-1] not in ".!?":
            return 0.7

        return 0.9  # Seems coherent

    async def _check_relevance(self, example: TrainingExample) -> float:
        """Check if output is relevant to input."""
        # For classification, the category is a high-level label, not direct word overlap
        if example.task_type == TaskType.CLASSIFICATION:
            return 0.9 if example.output_text.strip() else 0.0

        # Simplified: check for word overlap
        input_words = set(example.input_text.lower().split())
        output_words = set(example.output_text.lower().split())

        # Calculate overlap
        if not input_words:
            return 0.5

        overlap = len(input_words & output_words) / len(input_words)

        # Score based on overlap (not too little, not too much)
        if overlap < 0.1:
            return 0.4  # Too little overlap
        elif overlap > 0.9:
            return 0.6  # Too much overlap (might be copying)
        else:
            return 0.9  # Good relevance

    def _check_dataset_diversity(self, dataset: Dataset) -> float:
        """Check diversity of examples in dataset."""
        if len(dataset.examples) < 2:
            return 1.0

        # Check for duplicate or very similar examples
        seen_inputs = set()
        duplicates = 0

        for example in dataset.examples:
            # Normalize input for comparison
            normalized = example.input_text.lower().strip()

            if normalized in seen_inputs:
                duplicates += 1
            else:
                seen_inputs.add(normalized)

        # Score based on uniqueness
        uniqueness = (len(dataset.examples) - duplicates) / len(dataset.examples)

        return uniqueness

    def __repr__(self) -> str:
        """String representation."""
        return f"QualityEvaluator(threshold={self.threshold})"
