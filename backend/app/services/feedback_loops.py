"""Feedback Loops — Scheduled outcome checks for decision tracking.

Checks expected outcome dates and generates follow-up prompts
for the founder to compare predicted vs. actual results.
"""

import logging
from datetime import datetime, date

logger = logging.getLogger(__name__)


class FeedbackLoopService:
    """Manages decision outcome follow-ups."""

    def get_due_decisions(self, decisions: list[dict], check_date: date = None) -> list[dict]:
        """Find decisions whose expected outcome date has passed."""
        today = check_date or date.today()
        due = []

        for decision in decisions:
            if decision.get("status") != "pending":
                continue

            expected_date = decision.get("expected_outcome_date")
            if expected_date:
                if isinstance(expected_date, str):
                    expected_date = date.fromisoformat(expected_date)
                if expected_date <= today:
                    due.append(decision)

        return due

    def generate_followup_prompt(self, decision: dict) -> str:
        """Generate a follow-up prompt for a decision whose outcome date has passed."""
        title = decision.get("title", "your decision")
        expected = decision.get("expected_outcome", "the expected outcome")
        confidence = int(decision.get("confidence_score", 0) * 100)

        return (
            f"📊 **Decision Check-In: {title}**\n\n"
            f"When you made this decision, you expected: *{expected}*\n"
            f"Your confidence was {confidence}%.\n\n"
            f"**What actually happened?** Compare the real outcome to your prediction.\n"
            f"This isn't about being right — it's about calibrating your judgment over time."
        )

    def calculate_calibration_score(
        self,
        decisions: list[dict],
    ) -> dict:
        """Calculate confidence calibration metrics.
        
        Good calibration means 70% confident decisions are correct ~70% of the time.
        """
        if not decisions:
            return {"score": 0, "sample_size": 0, "details": []}

        resolved = [d for d in decisions if d.get("status") == "resolved"]
        if not resolved:
            return {"score": 0, "sample_size": 0, "details": []}

        # Group by confidence buckets
        buckets = {
            "50-60%": {"predicted": 0.55, "total": 0, "correct": 0},
            "60-70%": {"predicted": 0.65, "total": 0, "correct": 0},
            "70-80%": {"predicted": 0.75, "total": 0, "correct": 0},
            "80-90%": {"predicted": 0.85, "total": 0, "correct": 0},
            "90-100%": {"predicted": 0.95, "total": 0, "correct": 0},
        }

        for decision in resolved:
            confidence = decision.get("confidence_score", 0)
            outcome = decision.get("outcome_score", 0)

            if confidence < 0.6:
                bucket = "50-60%"
            elif confidence < 0.7:
                bucket = "60-70%"
            elif confidence < 0.8:
                bucket = "70-80%"
            elif confidence < 0.9:
                bucket = "80-90%"
            else:
                bucket = "90-100%"

            buckets[bucket]["total"] += 1
            if outcome >= 0.7:  # Consider "correct" if outcome score >= 0.7
                buckets[bucket]["correct"] += 1

        # Calculate Brier-like score (lower is better)
        total_error = 0
        counted = 0
        details = []

        for label, data in buckets.items():
            if data["total"] > 0:
                actual_rate = data["correct"] / data["total"]
                error = abs(data["predicted"] - actual_rate)
                total_error += error
                counted += 1
                details.append({
                    "bucket": label,
                    "predicted": data["predicted"],
                    "actual": actual_rate,
                    "count": data["total"],
                    "calibration_error": round(error, 3),
                })

        avg_error = total_error / counted if counted > 0 else 1
        score = max(0, round((1 - avg_error) * 100, 1))

        return {
            "score": score,
            "sample_size": len(resolved),
            "details": details,
        }


# Singleton
feedback_service = FeedbackLoopService()
