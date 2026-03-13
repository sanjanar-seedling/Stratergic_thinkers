"""State-Aware Prompter — Calendar context integration.

Queries calendar data before sending prompts to respect:
- Deep work blocks (suppress notifications)
- Maker vs Manager mode detection
- Transition moments (post-meeting reflection triggers)
"""

import logging
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


class StateAwarePrompter:
    """Manages context-aware prompt timing based on calendar state."""

    class FounderState:
        DEEP_WORK = "deep_work"
        MEETINGS = "meetings"
        TRANSITION = "transition"
        FREE = "free"
        UNKNOWN = "unknown"

    def detect_state(self, calendar_events: list[dict], current_time: datetime = None) -> str:
        """Detect the founder's current state from calendar data."""
        if not calendar_events:
            return self.FounderState.FREE

        now = current_time or datetime.now()

        # Check if currently in a meeting
        for event in calendar_events:
            start = event.get("start")
            end = event.get("end")
            if start and end and start <= now <= end:
                summary = event.get("summary", "").lower()
                if any(w in summary for w in ["focus", "deep work", "coding", "heads down"]):
                    return self.FounderState.DEEP_WORK
                return self.FounderState.MEETINGS

        # Check if just finished a meeting (transition window: 15 min after)
        for event in calendar_events:
            end = event.get("end")
            if end:
                minutes_since = (now - end).total_seconds() / 60
                if 0 <= minutes_since <= 15:
                    return self.FounderState.TRANSITION

        return self.FounderState.FREE

    def should_prompt(self, state: str) -> bool:
        """Decide whether to send a prompt in the current state."""
        suppressed_states = {
            self.FounderState.DEEP_WORK,
            self.FounderState.MEETINGS,
        }
        return state not in suppressed_states

    def get_context_prompt(self, state: str) -> Optional[str]:
        """Generate a context-appropriate prompt based on state."""
        if state == self.FounderState.TRANSITION:
            return (
                "You just wrapped up a meeting. "
                "Take 60 seconds: What's the one thing from that conversation "
                "that shifted your thinking?"
            )
        elif state == self.FounderState.FREE:
            return None  # No forced prompt during free time
        return None

    def detect_time_allocation_drift(
        self,
        stated_priorities: dict[str, float],
        actual_time: dict[str, float],
    ) -> list[dict]:
        """Compare stated priorities vs actual time allocation.
        
        Args:
            stated_priorities: {"engineering": 0.4, "sales": 0.3, ...}
            actual_time: {"engineering": 0.6, "sales": 0.1, ...}
        """
        drifts = []
        for category, target in stated_priorities.items():
            actual = actual_time.get(category, 0)
            drift = abs(actual - target)
            if drift > 0.15:  # More than 15% drift
                direction = "over" if actual > target else "under"
                drifts.append({
                    "category": category,
                    "target": target,
                    "actual": actual,
                    "drift": drift,
                    "direction": direction,
                    "message": f"You're {direction}-indexing on {category}: "
                              f"target {int(target*100)}% vs actual {int(actual*100)}%",
                })

        return sorted(drifts, key=lambda d: d["drift"], reverse=True)


# Singleton
state_prompter = StateAwarePrompter()
