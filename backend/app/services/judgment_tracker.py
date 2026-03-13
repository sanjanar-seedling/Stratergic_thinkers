"""Judgment Quality Tracking System.

Tracks decision outcomes over time to measure and improve judgment quality.

Key Metrics:
1. Accuracy Rate: % of predictions that matched actual outcomes
2. Calibration Score: How well confidence matches accuracy
3. Improvement Trend: Is judgment getting better over time?
4. Framework Effectiveness: Which frameworks lead to better outcomes?
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import DecisionOutcome, FounderEvent, FrameworkApplication

logger = logging.getLogger(__name__)


class JudgmentTracker:
    """Tracks and analyzes judgment quality over time."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_decision_outcome(
        self,
        user_id: UUID,
        decision_event_id: UUID,
        decision_summary: str,
        predicted_outcome: str,
        confidence_level: float,
        predicted_impact: str,
        frameworks_applied: List[str] = None,
        followup_days: int = 30,
    ) -> DecisionOutcome:
        """Create a new decision outcome record.
        
        Args:
            user_id: User ID
            decision_event_id: ID of the decision event
            decision_summary: Brief summary of the decision
            predicted_outcome: "success", "failure", or "neutral"
            confidence_level: 0.0 to 1.0 (how confident is the founder?)
            predicted_impact: "high", "medium", or "low"
            frameworks_applied: List of framework IDs used
            followup_days: When to check the outcome (default: 30 days)
        
        Returns:
            Created DecisionOutcome
        """
        outcome = DecisionOutcome(
            user_id=user_id,
            decision_event_id=decision_event_id,
            decision_summary=decision_summary,
            predicted_outcome=predicted_outcome,
            confidence_level=confidence_level,
            predicted_impact=predicted_impact,
            frameworks_applied=frameworks_applied or [],
            decision_date=datetime.utcnow(),
            followup_date=datetime.utcnow() + timedelta(days=followup_days),
        )

        self.db.add(outcome)
        await self.db.commit()
        await self.db.refresh(outcome)

        logger.info(
            f"Created decision outcome: {decision_summary[:50]} "
            f"(predicted: {predicted_outcome}, confidence: {confidence_level})"
        )

        return outcome

    async def record_actual_outcome(
        self,
        outcome_id: UUID,
        actual_outcome: str,
        actual_impact: str,
        outcome_notes: str,
    ) -> DecisionOutcome:
        """Record the actual outcome of a decision.
        
        Args:
            outcome_id: ID of the DecisionOutcome
            actual_outcome: "success", "failure", or "neutral"
            actual_impact: "high", "medium", or "low"
            outcome_notes: What actually happened
        
        Returns:
            Updated DecisionOutcome
        """
        result = await self.db.execute(
            select(DecisionOutcome).where(DecisionOutcome.id == outcome_id)
        )
        outcome = result.scalar_one_or_none()

        if not outcome:
            raise ValueError(f"DecisionOutcome {outcome_id} not found")

        # Update outcome
        outcome.actual_outcome = actual_outcome
        outcome.actual_impact = actual_impact
        outcome.outcome_notes = outcome_notes
        outcome.outcome_recorded_date = datetime.utcnow()

        # Calculate judgment quality
        outcome.was_correct = outcome.predicted_outcome == actual_outcome

        # Calibration error: |confidence - accuracy|
        accuracy = 1.0 if outcome.was_correct else 0.0
        outcome.calibration_error = abs(outcome.confidence_level - accuracy)

        await self.db.commit()
        await self.db.refresh(outcome)

        logger.info(
            f"Recorded outcome for {outcome.decision_summary[:50]}: "
            f"predicted={outcome.predicted_outcome}, actual={actual_outcome}, "
            f"correct={outcome.was_correct}, calibration_error={outcome.calibration_error:.2f}"
        )

        return outcome

    async def get_pending_followups(
        self,
        user_id: UUID,
    ) -> List[DecisionOutcome]:
        """Get decisions that need outcome follow-up.
        
        Returns decisions where:
        - followup_date has passed
        - actual_outcome is not yet recorded
        """
        result = await self.db.execute(
            select(DecisionOutcome)
            .where(
                and_(
                    DecisionOutcome.user_id == user_id,
                    DecisionOutcome.followup_date <= datetime.utcnow(),
                    DecisionOutcome.actual_outcome.is_(None),
                )
            )
            .order_by(DecisionOutcome.followup_date)
        )
        return result.scalars().all()

    async def calculate_judgment_metrics(
        self,
        user_id: UUID,
        lookback_days: int = 365,
    ) -> Dict:
        """Calculate comprehensive judgment quality metrics.
        
        Returns:
            {
                "total_decisions": int,
                "decisions_with_outcomes": int,
                "accuracy_rate": float,
                "average_confidence": float,
                "calibration_score": float,
                "improvement_trend": str,
                "by_framework": {...},
                "by_impact": {...},
            }
        """
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

        # Get all decision outcomes
        result = await self.db.execute(
            select(DecisionOutcome)
            .where(
                and_(
                    DecisionOutcome.user_id == user_id,
                    DecisionOutcome.decision_date >= cutoff_date,
                )
            )
            .order_by(DecisionOutcome.decision_date)
        )
        outcomes = result.scalars().all()

        total_decisions = len(outcomes)
        outcomes_with_results = [o for o in outcomes if o.actual_outcome is not None]
        decisions_with_outcomes = len(outcomes_with_results)

        if decisions_with_outcomes == 0:
            return {
                "total_decisions": total_decisions,
                "decisions_with_outcomes": 0,
                "accuracy_rate": 0.0,
                "average_confidence": 0.0,
                "calibration_score": 0.0,
                "improvement_trend": "insufficient_data",
                "by_framework": {},
                "by_impact": {},
            }

        # Calculate accuracy rate
        correct_predictions = sum(1 for o in outcomes_with_results if o.was_correct)
        accuracy_rate = correct_predictions / decisions_with_outcomes

        # Calculate average confidence
        confidences = [o.confidence_level for o in outcomes if o.confidence_level is not None]
        average_confidence = sum(confidences) / len(confidences) if confidences else 0.0

        # Calculate calibration score
        calibration_errors = [
            o.calibration_error for o in outcomes_with_results if o.calibration_error is not None
        ]
        calibration_score = (
            1.0 - (sum(calibration_errors) / len(calibration_errors))
            if calibration_errors
            else 0.0
        )

        # Calculate improvement trend
        improvement_trend = self._calculate_improvement_trend(outcomes_with_results)

        # Analyze by framework
        by_framework = await self._analyze_by_framework(user_id, outcomes_with_results)

        # Analyze by impact level
        by_impact = self._analyze_by_impact(outcomes_with_results)

        return {
            "total_decisions": total_decisions,
            "decisions_with_outcomes": decisions_with_outcomes,
            "accuracy_rate": accuracy_rate,
            "average_confidence": average_confidence,
            "calibration_score": calibration_score,
            "improvement_trend": improvement_trend,
            "by_framework": by_framework,
            "by_impact": by_impact,
        }

    def _calculate_improvement_trend(
        self,
        outcomes: List[DecisionOutcome],
    ) -> str:
        """Calculate if judgment is improving, stable, or declining."""
        if len(outcomes) < 10:
            return "insufficient_data"

        # Split into two halves
        mid = len(outcomes) // 2
        first_half = outcomes[:mid]
        second_half = outcomes[mid:]

        first_accuracy = sum(1 for o in first_half if o.was_correct) / len(first_half)
        second_accuracy = sum(1 for o in second_half if o.was_correct) / len(second_half)

        if second_accuracy > first_accuracy + 0.1:
            return "improving"
        elif second_accuracy < first_accuracy - 0.1:
            return "declining"
        else:
            return "stable"

    async def _analyze_by_framework(
        self,
        user_id: UUID,
        outcomes: List[DecisionOutcome],
    ) -> Dict:
        """Analyze which frameworks lead to better outcomes."""
        framework_stats = {}

        for outcome in outcomes:
            for framework_id in outcome.frameworks_applied or []:
                if framework_id not in framework_stats:
                    framework_stats[framework_id] = {
                        "total": 0,
                        "correct": 0,
                        "accuracy": 0.0,
                    }

                framework_stats[framework_id]["total"] += 1
                if outcome.was_correct:
                    framework_stats[framework_id]["correct"] += 1

        # Calculate accuracy for each framework
        for framework_id, stats in framework_stats.items():
            stats["accuracy"] = stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0

        return framework_stats

    def _analyze_by_impact(
        self,
        outcomes: List[DecisionOutcome],
    ) -> Dict:
        """Analyze accuracy by predicted impact level."""
        impact_stats = {"high": {"total": 0, "correct": 0}, "medium": {"total": 0, "correct": 0}, "low": {"total": 0, "correct": 0}}

        for outcome in outcomes:
            impact = outcome.predicted_impact
            if impact in impact_stats:
                impact_stats[impact]["total"] += 1
                if outcome.was_correct:
                    impact_stats[impact]["correct"] += 1

        # Calculate accuracy for each impact level
        for impact, stats in impact_stats.items():
            stats["accuracy"] = stats["correct"] / stats["total"] if stats["total"] > 0 else 0.0

        return impact_stats

    async def generate_judgment_report(
        self,
        user_id: UUID,
        lookback_days: int = 90,
    ) -> str:
        """Generate a natural language report on judgment quality.
        
        Returns:
            Markdown-formatted report
        """
        metrics = await self.calculate_judgment_metrics(user_id, lookback_days)

        report = f"""# Judgment Quality Report

## Overview
- **Total Decisions**: {metrics['total_decisions']}
- **Decisions with Outcomes**: {metrics['decisions_with_outcomes']}
- **Accuracy Rate**: {metrics['accuracy_rate']*100:.1f}%
- **Calibration Score**: {metrics['calibration_score']*100:.1f}%
- **Trend**: {metrics['improvement_trend'].replace('_', ' ').title()}

## Insights

### Calibration
Your calibration score of {metrics['calibration_score']*100:.1f}% means your confidence levels {'match' if metrics['calibration_score'] > 0.8 else 'do not match'} your actual accuracy.

{'**Well calibrated!** You have a good sense of when you\'re right.' if metrics['calibration_score'] > 0.8 else '**Calibration opportunity:** You may be over-confident or under-confident in your predictions.'}

### Trend
{'**Improving!** Your judgment quality is getting better over time.' if metrics['improvement_trend'] == 'improving' else '**Stable:** Your judgment quality is consistent.' if metrics['improvement_trend'] == 'stable' else '**Declining:** Your recent decisions have been less accurate.' if metrics['improvement_trend'] == 'declining' else 'Not enough data to determine trend yet.'}

## Framework Effectiveness

"""

        if metrics["by_framework"]:
            report += "\n| Framework | Decisions | Accuracy |\n|-----------|-----------|----------|\n"
            for framework_id, stats in sorted(
                metrics["by_framework"].items(), key=lambda x: x[1]["accuracy"], reverse=True
            ):
                report += f"| {framework_id} | {stats['total']} | {stats['accuracy']*100:.1f}% |\n"
        else:
            report += "No framework data yet.\n"

        return report


if __name__ == "__main__":
    import asyncio
    from app.core.database import get_db

    async def test_judgment_tracker():
        async for db in get_db():
            tracker = JudgmentTracker(db)

            # Example: Create a decision outcome
            # outcome = await tracker.create_decision_outcome(
            #     user_id=UUID("..."),
            #     decision_event_id=UUID("..."),
            #     decision_summary="Decided to pivot product strategy",
            #     predicted_outcome="success",
            #     confidence_level=0.7,
            #     predicted_impact="high",
            #     frameworks_applied=["first-principles", "regret-minimization"],
            #     followup_days=60,
            # )

            # Example: Get metrics
            # metrics = await tracker.calculate_judgment_metrics(user_id=UUID("..."))
            # print(metrics)

            break

    asyncio.run(test_judgment_tracker())
