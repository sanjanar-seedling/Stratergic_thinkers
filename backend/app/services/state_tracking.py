"""State & Drift Tracking Engine.

Monitors:
1. Emotional state correlation with decision quality
2. Time allocation drift (stated priorities vs. actual time spent)
3. Energy level patterns
4. Context switching frequency
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class EmotionalState(BaseModel):
    """Detected emotional state from text."""

    timestamp: str
    primary_emotion: str  # "confident", "anxious", "frustrated", "excited"
    intensity: float  # 0.0 to 1.0
    keywords: List[str]


class TimeAllocationDrift(BaseModel):
    """Detected drift between stated priorities and actual time."""

    category: str
    stated_priority: float  # 0.0 to 1.0 (from weekly reviews)
    actual_time: float  # 0.0 to 1.0 (from calendar data)
    drift_percentage: float
    severity: str  # "low", "medium", "high"
    recommendation: str


class StateTrackingEngine:
    """Tracks founder state and detects drift patterns."""

    def __init__(self):
        self.emotion_keywords = {
            "confident": [
                "confident",
                "certain",
                "clear",
                "sure",
                "convinced",
                "momentum",
            ],
            "anxious": [
                "worried",
                "anxious",
                "nervous",
                "uncertain",
                "stressed",
                "overwhelmed",
            ],
            "frustrated": [
                "frustrated",
                "stuck",
                "blocked",
                "annoyed",
                "irritated",
            ],
            "excited": [
                "excited",
                "energized",
                "pumped",
                "thrilled",
                "motivated",
            ],
            "burned_out": [
                "exhausted",
                "drained",
                "tired",
                "burned out",
                "depleted",
            ],
        }

    def detect_emotional_state(
        self,
        text: str,
        timestamp: str,
    ) -> Optional[EmotionalState]:
        """Detect emotional state from text content."""
        text_lower = text.lower()
        detected_emotions = {}

        for emotion, keywords in self.emotion_keywords.items():
            matches = [kw for kw in keywords if kw in text_lower]
            if matches:
                # Simple intensity: number of keyword matches
                intensity = min(len(matches) / 3, 1.0)
                detected_emotions[emotion] = (intensity, matches)

        if not detected_emotions:
            return None

        # Primary emotion = highest intensity
        primary = max(detected_emotions.items(), key=lambda x: x[1][0])
        emotion_name, (intensity, keywords) = primary

        return EmotionalState(
            timestamp=timestamp,
            primary_emotion=emotion_name,
            intensity=intensity,
            keywords=keywords,
        )

    def analyze_emotional_patterns(
        self,
        events: List[dict],
        lookback_days: int = 30,
    ) -> Dict[str, any]:
        """Analyze emotional state patterns over time."""
        cutoff = datetime.utcnow() - timedelta(days=lookback_days)
        recent_events = [
            e
            for e in events
            if datetime.fromisoformat(e.get("created_at", "")) > cutoff
        ]

        emotion_timeline = []
        emotion_counts = defaultdict(int)

        for event in recent_events:
            state = self.detect_emotional_state(
                event.get("text", ""),
                event.get("created_at"),
            )
            if state:
                emotion_timeline.append(state)
                emotion_counts[state.primary_emotion] += 1

        # Calculate dominant emotion
        dominant_emotion = None
        if emotion_counts:
            dominant_emotion = max(emotion_counts.items(), key=lambda x: x[1])[0]

        # Detect emotional volatility (rapid changes)
        volatility_score = self._calculate_emotional_volatility(emotion_timeline)

        return {
            "dominant_emotion": dominant_emotion,
            "emotion_distribution": dict(emotion_counts),
            "volatility_score": volatility_score,
            "timeline": [e.dict() for e in emotion_timeline],
        }

    def _calculate_emotional_volatility(self, timeline: List[EmotionalState]) -> float:
        """Calculate how frequently emotional state changes.
        
        Returns:
            0.0 = stable, 1.0 = highly volatile
        """
        if len(timeline) < 2:
            return 0.0

        changes = 0
        for i in range(1, len(timeline)):
            if timeline[i].primary_emotion != timeline[i - 1].primary_emotion:
                changes += 1

        return min(changes / len(timeline), 1.0)

    def detect_time_allocation_drift(
        self,
        stated_priorities: Dict[str, float],
        actual_time: Dict[str, float],
        threshold: float = 0.2,
    ) -> List[TimeAllocationDrift]:
        """Detect drift between stated priorities and actual time spent.
        
        Args:
            stated_priorities: {"engineering": 0.5, "fundraising": 0.3, ...}
            actual_time: {"engineering": 0.3, "fundraising": 0.5, ...}
            threshold: Minimum drift to report (0.2 = 20%)
        
        Returns:
            List of detected drifts
        """
        drifts = []

        all_categories = set(stated_priorities.keys()) | set(actual_time.keys())

        for category in all_categories:
            stated = stated_priorities.get(category, 0.0)
            actual = actual_time.get(category, 0.0)
            drift = actual - stated

            if abs(drift) >= threshold:
                severity = (
                    "high" if abs(drift) >= 0.4 else "medium" if abs(drift) >= 0.25 else "low"
                )

                recommendation = self._generate_drift_recommendation(
                    category, drift, stated, actual
                )

                drifts.append(
                    TimeAllocationDrift(
                        category=category,
                        stated_priority=stated,
                        actual_time=actual,
                        drift_percentage=drift * 100,
                        severity=severity,
                        recommendation=recommendation,
                    )
                )

        return drifts

    def _generate_drift_recommendation(
        self,
        category: str,
        drift: float,
        stated: float,
        actual: float,
    ) -> str:
        """Generate actionable recommendation for drift."""
        if drift > 0:
            # Spending more time than intended
            return (
                f"You're spending {abs(drift)*100:.0f}% more time on {category} "
                f"than planned. Consider: Is this the right priority shift, or are "
                f"you being pulled into reactive work?"
            )
        else:
            # Spending less time than intended
            return (
                f"You're spending {abs(drift)*100:.0f}% less time on {category} "
                f"than planned. Consider: What's blocking you from this priority? "
                f"Is it avoidance or legitimate reprioritization?"
            )

    def correlate_emotion_with_decisions(
        self,
        events: List[dict],
    ) -> Dict[str, any]:
        """Correlate emotional state with decision quality.
        
        Note: Decision quality requires retrospective outcome data.
        This is a placeholder for future implementation.
        """
        decision_events = [
            e for e in events if e.get("event_type") == "decision_record"
        ]

        emotion_at_decision = []
        for event in decision_events:
            state = self.detect_emotional_state(
                event.get("text", ""),
                event.get("created_at"),
            )
            if state:
                emotion_at_decision.append(
                    {
                        "event_id": event.get("id"),
                        "emotion": state.primary_emotion,
                        "intensity": state.intensity,
                        "timestamp": event.get("created_at"),
                    }
                )

        return {
            "total_decisions": len(decision_events),
            "decisions_with_emotion_data": len(emotion_at_decision),
            "emotion_breakdown": emotion_at_decision,
        }


if __name__ == "__main__":
    # Example usage
    engine = StateTrackingEngine()

    # Detect emotional state
    state = engine.detect_emotional_state(
        "I'm feeling really anxious about this fundraising round. "
        "Worried we won't hit our targets.",
        "2026-03-08T10:00:00",
    )
    print(f"Detected: {state.primary_emotion} (intensity: {state.intensity})")

    # Detect time allocation drift
    stated = {"engineering": 0.5, "fundraising": 0.3, "hiring": 0.2}
    actual = {"engineering": 0.2, "fundraising": 0.6, "hiring": 0.2}
    drifts = engine.detect_time_allocation_drift(stated, actual)

    for drift in drifts:
        print(f"\n{drift.category}: {drift.drift_percentage:+.0f}% drift ({drift.severity})")
        print(f"  {drift.recommendation}")
