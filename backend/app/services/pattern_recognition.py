"""Pattern Recognition Engine.

Analyzes founder events to detect:
1. Recurring choice frameworks
2. Cognitive biases (sunk cost, confirmation bias, etc.)
3. Avoidance patterns (topics consistently delayed)
4. Over-optimization traps (perfecting instead of executing)
"""

import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class PatternInsight(BaseModel):
    """Detected pattern with confidence score."""

    pattern_type: str
    description: str
    confidence: float  # 0.0 to 1.0
    evidence: List[str]  # Event IDs supporting this pattern
    first_detected: str
    last_seen: str
    frequency: int
    metadata: Dict = {}


class CognitiveBias(BaseModel):
    """Detected cognitive bias."""

    bias_name: str
    description: str
    severity: str  # "low", "medium", "high"
    examples: List[str]
    recommendation: str


class PatternRecognitionEngine:
    """Analyzes event history to detect patterns and biases."""

    def __init__(self):
        self.decision_keywords = {
            "sunk_cost": [
                "already invested",
                "too far in",
                "can't give up now",
                "wasted effort",
                "so much time",
            ],
            "confirmation_bias": [
                "proves I was right",
                "validates my",
                "confirms that",
                "as I suspected",
            ],
            "analysis_paralysis": [
                "need more data",
                "not enough information",
                "waiting for",
                "researching",
                "analyzing",
            ],
            "over_optimization": [
                "perfect",
                "refining",
                "polishing",
                "tweaking",
                "optimizing",
            ],
        }

    def analyze_decision_patterns(
        self,
        events: List[dict],
        lookback_days: int = 90,
    ) -> List[PatternInsight]:
        """Analyze decision-making patterns over time.
        
        Args:
            events: List of FounderEvent dicts
            lookback_days: How far back to analyze
        
        Returns:
            List of detected patterns
        """
        patterns = []
        cutoff_date = datetime.utcnow() - timedelta(days=lookback_days)

        # Filter to decision events within lookback window
        decision_events = [
            e
            for e in events
            if e.get("event_type") == "decision_record"
            and datetime.fromisoformat(e.get("created_at", "")) > cutoff_date
        ]

        if len(decision_events) < 3:
            return patterns

        # Detect recurring frameworks
        framework_pattern = self._detect_framework_patterns(decision_events)
        if framework_pattern:
            patterns.append(framework_pattern)

        # Detect decision velocity changes
        velocity_pattern = self._detect_decision_velocity(decision_events)
        if velocity_pattern:
            patterns.append(velocity_pattern)

        return patterns

    def _detect_framework_patterns(self, events: List[dict]) -> Optional[PatternInsight]:
        """Detect if founder consistently uses specific decision frameworks."""
        frameworks = {
            "pros_cons": ["pros", "cons", "advantages", "disadvantages"],
            "first_principles": ["first principles", "fundamental", "core assumption"],
            "reversible": ["reversible", "one-way door", "two-way door"],
            "regret_minimization": ["regret", "looking back", "future self"],
        }

        framework_counts = Counter()
        framework_evidence = defaultdict(list)

        for event in events:
            text = event.get("text", "").lower()
            for framework, keywords in frameworks.items():
                if any(kw in text for kw in keywords):
                    framework_counts[framework] += 1
                    framework_evidence[framework].append(event.get("id"))

        # If a framework appears in 40%+ of decisions, it's a pattern
        total_decisions = len(events)
        for framework, count in framework_counts.items():
            if count / total_decisions >= 0.4:
                return PatternInsight(
                    pattern_type="decision_framework",
                    description=f"Consistently uses '{framework}' framework",
                    confidence=min(count / total_decisions, 1.0),
                    evidence=framework_evidence[framework],
                    first_detected=events[0].get("created_at"),
                    last_seen=events[-1].get("created_at"),
                    frequency=count,
                    metadata={"framework": framework},
                )

        return None

    def _detect_decision_velocity(self, events: List[dict]) -> Optional[PatternInsight]:
        """Detect if decision-making is speeding up or slowing down."""
        if len(events) < 6:
            return None

        # Split into two halves
        mid = len(events) // 2
        first_half = events[:mid]
        second_half = events[mid:]

        # Calculate decisions per week
        def decisions_per_week(event_list):
            if not event_list:
                return 0
            start = datetime.fromisoformat(event_list[0].get("created_at"))
            end = datetime.fromisoformat(event_list[-1].get("created_at"))
            weeks = max((end - start).days / 7, 1)
            return len(event_list) / weeks

        first_velocity = decisions_per_week(first_half)
        second_velocity = decisions_per_week(second_half)

        # Significant change = 50%+ difference
        if second_velocity > first_velocity * 1.5:
            return PatternInsight(
                pattern_type="decision_velocity",
                description="Decision velocity increasing (executing faster)",
                confidence=0.8,
                evidence=[e.get("id") for e in second_half],
                first_detected=second_half[0].get("created_at"),
                last_seen=second_half[-1].get("created_at"),
                frequency=len(second_half),
                metadata={
                    "first_half_velocity": round(first_velocity, 2),
                    "second_half_velocity": round(second_velocity, 2),
                },
            )
        elif second_velocity < first_velocity * 0.5:
            return PatternInsight(
                pattern_type="decision_velocity",
                description="Decision velocity decreasing (analysis paralysis?)",
                confidence=0.8,
                evidence=[e.get("id") for e in second_half],
                first_detected=second_half[0].get("created_at"),
                last_seen=second_half[-1].get("created_at"),
                frequency=len(second_half),
                metadata={
                    "first_half_velocity": round(first_velocity, 2),
                    "second_half_velocity": round(second_velocity, 2),
                },
            )

        return None

    def detect_cognitive_biases(
        self,
        events: List[dict],
    ) -> List[CognitiveBias]:
        """Detect cognitive biases in decision-making."""
        biases = []

        for bias_name, keywords in self.decision_keywords.items():
            matching_events = []
            for event in events:
                text = event.get("text", "").lower()
                if any(kw in text for kw in keywords):
                    matching_events.append(event.get("id"))

            if len(matching_events) >= 2:
                bias = self._create_bias_insight(bias_name, matching_events)
                biases.append(bias)

        return biases

    def _create_bias_insight(
        self,
        bias_name: str,
        examples: List[str],
    ) -> CognitiveBias:
        """Create bias insight with recommendations."""
        bias_info = {
            "sunk_cost": {
                "description": "Continuing a path because of past investment, not future value",
                "recommendation": "Ask: 'If I started today, would I choose this path?'",
            },
            "confirmation_bias": {
                "description": "Seeking information that confirms existing beliefs",
                "recommendation": "Actively seek disconfirming evidence. Ask: 'What would prove me wrong?'",
            },
            "analysis_paralysis": {
                "description": "Delaying decisions while gathering more information",
                "recommendation": "Set decision deadlines. Ask: 'What's the minimum info needed to decide?'",
            },
            "over_optimization": {
                "description": "Perfecting details instead of shipping and learning",
                "recommendation": "Ship at 80% quality. Ask: 'What's the smallest version that tests the hypothesis?'",
            },
        }

        info = bias_info.get(bias_name, {})
        severity = "high" if len(examples) >= 5 else "medium" if len(examples) >= 3 else "low"

        return CognitiveBias(
            bias_name=bias_name.replace("_", " ").title(),
            description=info.get("description", ""),
            severity=severity,
            examples=examples[:5],  # Limit to 5 examples
            recommendation=info.get("recommendation", ""),
        )

    def detect_avoidance_patterns(
        self,
        events: List[dict],
        lookback_days: int = 30,
    ) -> List[PatternInsight]:
        """Detect topics the founder consistently avoids or delays."""
        patterns = []

        # Extract topics mentioned in reflections
        topic_mentions = defaultdict(list)
        topic_decisions = defaultdict(list)

        for event in events:
            text = event.get("text", "").lower()
            event_type = event.get("event_type")
            created_at = event.get("created_at")

            # Common founder topics
            topics = {
                "fundraising": ["fundraising", "investors", "pitch", "capital"],
                "hiring": ["hiring", "recruiting", "team", "talent"],
                "product": ["product", "feature", "roadmap", "build"],
                "sales": ["sales", "revenue", "customers", "pipeline"],
                "marketing": ["marketing", "growth", "acquisition", "brand"],
            }

            for topic, keywords in topics.items():
                if any(kw in text for kw in keywords):
                    topic_mentions[topic].append(created_at)
                    if event_type == "decision_record":
                        topic_decisions[topic].append(event.get("id"))

        # Detect avoidance: mentioned frequently but no decisions
        for topic, mentions in topic_mentions.items():
            if len(mentions) >= 3 and len(topic_decisions.get(topic, [])) == 0:
                patterns.append(
                    PatternInsight(
                        pattern_type="avoidance",
                        description=f"Frequently mentions '{topic}' but avoids making decisions",
                        confidence=0.7,
                        evidence=mentions[:5],
                        first_detected=min(mentions),
                        last_seen=max(mentions),
                        frequency=len(mentions),
                        metadata={"topic": topic},
                    )
                )

        return patterns


if __name__ == "__main__":
    # Example usage
    engine = PatternRecognitionEngine()

    sample_events = [
        {
            "id": "1",
            "event_type": "decision_record",
            "text": "Decided to use pros/cons list for hiring decision",
            "created_at": "2026-01-15T10:00:00",
        },
        {
            "id": "2",
            "event_type": "decision_record",
            "text": "We've already invested so much time in this feature, can't give up now",
            "created_at": "2026-02-01T14:00:00",
        },
    ]

    patterns = engine.analyze_decision_patterns(sample_events)
    biases = engine.detect_cognitive_biases(sample_events)

    print(f"Patterns: {len(patterns)}")
    print(f"Biases: {len(biases)}")
