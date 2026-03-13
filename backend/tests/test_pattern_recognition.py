"""Unit Tests for Pattern Recognition Engine."""

import pytest
from datetime import datetime, timedelta

from app.services.pattern_recognition import (
    PatternRecognitionEngine,
    PatternInsight,
    CognitiveBias,
)


@pytest.fixture
def pattern_engine():
    return PatternRecognitionEngine()


@pytest.fixture
def sample_events():
    base_date = datetime.utcnow()
    return [
        {
            "id": "1",
            "event_type": "decision_record",
            "text": "Decided to use pros and cons list for hiring decision. Weighing advantages and disadvantages carefully.",
            "created_at": (base_date - timedelta(days=10)).isoformat(),
        },
        {
            "id": "2",
            "event_type": "decision_record",
            "text": "We've already invested so much time in this feature, can't give up now. Too far in to quit.",
            "created_at": (base_date - timedelta(days=8)).isoformat(),
        },
        {
            "id": "3",
            "event_type": "decision_record",
            "text": "Using pros/cons framework again for product decision. This approach works well for me.",
            "created_at": (base_date - timedelta(days=5)).isoformat(),
        },
        {
            "id": "4",
            "event_type": "decision_record",
            "text": "This data confirms my hypothesis. Validates my initial thinking about the market.",
            "created_at": (base_date - timedelta(days=3)).isoformat(),
        },
        {
            "id": "5",
            "event_type": "reflection",
            "text": "Keep thinking about fundraising but haven't made any decisions yet.",
            "created_at": (base_date - timedelta(days=2)).isoformat(),
        },
        {
            "id": "6",
            "event_type": "reflection",
            "text": "Fundraising is on my mind again. Need to think about this more.",
            "created_at": (base_date - timedelta(days=1)).isoformat(),
        },
    ]


class TestPatternRecognition:
    def test_detect_framework_patterns(self, pattern_engine, sample_events):
        """Test detection of recurring decision frameworks."""
        patterns = pattern_engine.analyze_decision_patterns(sample_events)
        
        # Should detect pros/cons framework pattern
        framework_patterns = [p for p in patterns if p.pattern_type == "decision_framework"]
        assert len(framework_patterns) > 0
        
        # Check pattern details
        pros_cons_pattern = framework_patterns[0]
        assert "pros_cons" in pros_cons_pattern.metadata.get("framework", "")
        assert pros_cons_pattern.confidence >= 0.4

    def test_detect_cognitive_biases(self, pattern_engine, sample_events):
        """Test detection of cognitive biases."""
        biases = pattern_engine.detect_cognitive_biases(sample_events)
        
        # Should detect sunk cost fallacy
        sunk_cost_biases = [b for b in biases if "sunk" in b.bias_name.lower()]
        assert len(sunk_cost_biases) > 0
        
        # Should detect confirmation bias
        confirmation_biases = [b for b in biases if "confirmation" in b.bias_name.lower()]
        assert len(confirmation_biases) > 0

    def test_detect_avoidance_patterns(self, pattern_engine, sample_events):
        """Test detection of avoidance patterns."""
        avoidance = pattern_engine.detect_avoidance_patterns(sample_events)
        
        # Should detect fundraising avoidance
        fundraising_avoidance = [a for a in avoidance if "fundraising" in a.metadata.get("topic", "")]
        assert len(fundraising_avoidance) > 0
        
        # Check avoidance details
        pattern = fundraising_avoidance[0]
        assert pattern.pattern_type == "avoidance"
        assert pattern.frequency >= 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
