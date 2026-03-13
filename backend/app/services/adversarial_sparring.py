"""Adversarial Sparring — Devil's Advocate engine.

Detects high-confidence decisions with no alternatives logged and
generates challenging prompts to identify perspective gaps.

Uses the swappable LLM provider for generation.
"""

import logging

from app.core.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)


class AdversarialSparring:
    """Generates challenging counter-arguments to stress-test founder decisions."""

    # System message sets the role — keeps it out of the echoed output
    SPARRING_SYSTEM = "You are a tough but fair board member. You challenge founders to think harder. Be direct, specific, and concise. Never repeat instructions."

    # Minimal user prompt — small models echo long prompts back
    SPARRING_PROMPT = """Challenge this decision in 3-4 short sentences:

Decision: {title}
Rationale: {rationale}
Confidence: {confidence}%
Alternatives considered: {alternatives}

Point out ONE blind spot or untested assumption. Name any cognitive bias. Ask ONE sharp question."""

    DEVIL_ADVOCATE_PROMPT = """Decision being defended: {conversation_history}

Founder says: "{user_message}"

In 2-3 sentences: acknowledge their point, then find the next weak link."""

    def should_trigger(self, decision: dict) -> bool:
        """Check if a decision should trigger adversarial sparring."""
        confidence = decision.get("confidence_score", 0)
        alternatives = decision.get("alternatives", [])

        # Trigger if high confidence with no alternatives
        if confidence >= 0.8 and len(alternatives) == 0:
            return True

        # Trigger if very high confidence
        if confidence >= 0.9:
            return True

        return False

    async def generate_challenge(self, decision: dict) -> str:
        """Generate an adversarial challenge for a decision."""
        provider = get_llm_provider()

        try:
            alternatives_text = ", ".join(decision.get("alternatives", [])) or "None logged"

            prompt = self.SPARRING_PROMPT.format(
                title=decision.get("title", ""),
                rationale=decision.get("rationale", ""),
                confidence=int(decision.get("confidence_score", 0) * 100),
                alternatives=alternatives_text,
            )

            response = await provider.chat(
                [
                    {"role": "system", "content": self.SPARRING_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )
            return response.strip() or "Consider: What would a skeptical board member say about this decision?"
        except Exception as e:
            logger.error(f"Sparring generation failed: {e}")
            return "Consider: What would a skeptical board member say about this decision? What assumptions haven't you tested?"

    async def continue_sparring(
        self,
        conversation_history: str,
        user_message: str,
    ) -> str:
        """Continue an adversarial sparring conversation."""
        provider = get_llm_provider()

        try:
            prompt = self.DEVIL_ADVOCATE_PROMPT.format(
                conversation_history=conversation_history,
                user_message=user_message,
            )

            response = await provider.chat(
                [
                    {"role": "system", "content": self.SPARRING_SYSTEM},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
            )
            return response.strip() or "That's a fair point. But have you considered the second-order effects?"
        except Exception as e:
            logger.error(f"Sparring continuation failed: {e}")
            return "I hear you. Let me think about that angle differently."


# Singleton
adversarial_sparring = AdversarialSparring()
