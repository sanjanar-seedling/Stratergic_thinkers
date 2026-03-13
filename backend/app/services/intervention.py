"""Intervention Engine.

Determines when and how to intervene with reflection prompts.
Implements intelligent timing and Socratic questioning.

Intervention Types:
1. Pattern-triggered (e.g., detected cognitive bias)
2. Time-based (e.g., weekly review reminder)
3. Context-aware (e.g., after major decision)
4. Drift-triggered (e.g., time allocation mismatch)
"""

import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class InterventionPrompt(BaseModel):
    """A reflection prompt or question for the founder."""

    id: str
    trigger_type: str  # "pattern", "time", "context", "drift"
    prompt_type: str  # "clarifying", "challenging", "integrating"
    question: str
    context: str  # Why this question now
    priority: str  # "low", "medium", "high"
    created_at: str
    expires_at: Optional[str] = None


class InterventionEngine:
    """Generates context-aware reflection prompts."""

    def __init__(self, llm_provider):
        self.llm = llm_provider

    async def generate_bias_intervention(
        self,
        bias_name: str,
        evidence: List[str],
    ) -> InterventionPrompt:
        """Generate intervention for detected cognitive bias."""
        bias_prompts = {
            "sunk_cost": [
                "If you were starting fresh today with no prior investment, would you still choose this path?",
                "What would you tell a friend in this situation who hadn't already invested time/money?",
                "What's the opportunity cost of continuing vs. cutting losses now?",
            ],
            "confirmation_bias": [
                "What evidence would prove your current hypothesis wrong?",
                "Who disagrees with this decision, and what's their strongest argument?",
                "What are you not seeing because you're looking for confirmation?",
            ],
            "analysis_paralysis": [
                "What's the minimum information you need to make this decision?",
                "If you had to decide in the next hour, what would you choose?",
                "What's the cost of delaying this decision another week?",
            ],
            "over_optimization": [
                "What's the smallest version you could ship to test this hypothesis?",
                "At what point does 'better' become the enemy of 'done'?",
                "What would 80% quality look like, and would that be enough?",
            ],
        }

        questions = bias_prompts.get(bias_name, [])
        if not questions:
            question = "What assumptions are you making that might not be true?"
        else:
            # Rotate through questions
            question = questions[len(evidence) % len(questions)]

        return InterventionPrompt(
            id=f"bias-{bias_name}-{datetime.utcnow().timestamp()}",
            trigger_type="pattern",
            prompt_type="challenging",
            question=question,
            context=f"Detected {bias_name.replace('_', ' ')} pattern in recent decisions",
            priority="high",
            created_at=datetime.utcnow().isoformat(),
            expires_at=(datetime.utcnow() + timedelta(days=3)).isoformat(),
        )

    async def generate_drift_intervention(
        self,
        category: str,
        drift_percentage: float,
    ) -> InterventionPrompt:
        """Generate intervention for time allocation drift."""
        if drift_percentage > 0:
            # Spending more time than planned
            question = (
                f"You're spending {abs(drift_percentage):.0f}% more time on {category} "
                f"than you planned. Is this a conscious priority shift, or are you being "
                f"pulled into reactive work?"
            )
        else:
            # Spending less time than planned
            question = (
                f"You planned to spend more time on {category}, but you're not. "
                f"What's the real blocker? Is it avoidance, or has the priority legitimately changed?"
            )

        return InterventionPrompt(
            id=f"drift-{category}-{datetime.utcnow().timestamp()}",
            trigger_type="drift",
            prompt_type="clarifying",
            question=question,
            context=f"Time allocation drift detected: {category}",
            priority="medium",
            created_at=datetime.utcnow().isoformat(),
            expires_at=(datetime.utcnow() + timedelta(days=7)).isoformat(),
        )

    async def generate_decision_followup(
        self,
        decision_text: str,
        days_since: int = 7,
    ) -> InterventionPrompt:
        """Generate follow-up question for past decision."""
        prompt = f"""A founder made this decision {days_since} days ago:

{decision_text}

Generate a thoughtful follow-up question to help them reflect on:
1. What they've learned since making the decision
2. Whether their assumptions held true
3. What they'd do differently

Question (1-2 sentences):"""

        messages = [{"role": "user", "content": prompt}]
        question = await self.llm.chat(messages, temperature=0.5)

        return InterventionPrompt(
            id=f"followup-{datetime.utcnow().timestamp()}",
            trigger_type="context",
            prompt_type="integrating",
            question=question.strip(),
            context=f"Follow-up on decision from {days_since} days ago",
            priority="low",
            created_at=datetime.utcnow().isoformat(),
        )

    async def generate_weekly_review_prompt(
        self,
        last_week_summary: Optional[str] = None,
    ) -> InterventionPrompt:
        """Generate weekly review prompt."""
        base_questions = [
            "What was your biggest win this week?",
            "What decision are you avoiding?",
            "What did you learn that changed your thinking?",
            "Where did you spend time that didn't align with your priorities?",
            "What would you do differently next week?",
        ]

        if last_week_summary:
            # Generate personalized question based on last week
            prompt = f"""Last week, the founder reflected:

{last_week_summary}

Generate a thoughtful follow-up question for this week's review that builds on last week's insights.

Question:"""
            messages = [{"role": "user", "content": prompt}]
            question = await self.llm.chat(messages, temperature=0.5)
        else:
            # Use base questions
            question = "\n".join(f"{i+1}. {q}" for i, q in enumerate(base_questions))

        return InterventionPrompt(
            id=f"weekly-{datetime.utcnow().timestamp()}",
            trigger_type="time",
            prompt_type="integrating",
            question=question.strip(),
            context="Weekly review",
            priority="medium",
            created_at=datetime.utcnow().isoformat(),
            expires_at=(datetime.utcnow() + timedelta(days=7)).isoformat(),
        )

    async def generate_avoidance_intervention(
        self,
        topic: str,
        mention_count: int,
    ) -> InterventionPrompt:
        """Generate intervention for avoidance pattern."""
        question = (
            f"You've mentioned {topic} {mention_count} times recently, "
            f"but haven't made any decisions about it. What's the real blocker? "
            f"What would need to be true for you to take action?"
        )

        return InterventionPrompt(
            id=f"avoidance-{topic}-{datetime.utcnow().timestamp()}",
            trigger_type="pattern",
            prompt_type="challenging",
            question=question,
            context=f"Avoidance pattern detected: {topic}",
            priority="high",
            created_at=datetime.utcnow().isoformat(),
            expires_at=(datetime.utcnow() + timedelta(days=3)).isoformat(),
        )

    def should_intervene(
        self,
        last_intervention: Optional[datetime],
        priority: str,
        user_preferences: Optional[Dict] = None,
    ) -> bool:
        """Determine if it's appropriate to send an intervention now.
        
        Respects:
        - Minimum time between interventions
        - User-defined quiet hours
        - Intervention frequency preferences
        """
        # Default: don't spam
        min_hours_between = {
            "low": 48,
            "medium": 24,
            "high": 12,
        }

        if last_intervention:
            hours_since = (datetime.utcnow() - last_intervention).total_seconds() / 3600
            if hours_since < min_hours_between.get(priority, 24):
                return False

        # Check user preferences
        if user_preferences:
            # Check if in pause mode
            if user_preferences.get("pause_interventions"):
                return False

            # Check quiet hours
            quiet_start = user_preferences.get("quiet_hours_start")
            quiet_end = user_preferences.get("quiet_hours_end")
            if quiet_start and quiet_end:
                current_hour = datetime.utcnow().hour
                # Simple check (doesn't handle overnight ranges)
                if quiet_start <= current_hour < quiet_end:
                    return False

        return True


if __name__ == "__main__":
    import asyncio
    from app.core.llm_provider import get_llm_provider

    async def test_interventions():
        llm = get_llm_provider()
        engine = InterventionEngine(llm)

        # Test bias intervention
        bias_prompt = await engine.generate_bias_intervention(
            "sunk_cost",
            ["event-1", "event-2"],
        )
        print(f"\nBias Intervention: {bias_prompt.question}")

        # Test drift intervention
        drift_prompt = await engine.generate_drift_intervention(
            "fundraising",
            30.0,
        )
        print(f"\nDrift Intervention: {drift_prompt.question}")

        # Test weekly review
        weekly_prompt = await engine.generate_weekly_review_prompt()
        print(f"\nWeekly Review:\n{weekly_prompt.question}")

    asyncio.run(test_interventions())
