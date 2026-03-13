"""Inference Router — Decides how to respond to each FounderEvent.

Uses the swappable LLM provider to classify incoming events and route them to:
1. RAG query → recommend a mental model or framework
2. Clarifying question → Socratic probing
3. Pattern alert → flag a cognitive bias or avoidance
4. Acknowledgment → simple receipt of reflection
"""

import logging

from app.core.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)


class InferenceRouter:
    """Routes FounderEvents to the appropriate response strategy."""

    CLASSIFICATION_PROMPT = """You are a cognitive analysis engine for founders.
Given the following founder reflection or observation, classify it into one of these categories:

1. "rag_query" - The founder is wrestling with a strategic decision and would benefit from a relevant mental model or framework from the knowledge base.
2. "clarifying_question" - The founder's reflection is vague or surface-level. Ask a Socratic question to deepen their thinking.
3. "pattern_alert" - The text contains signals of cognitive bias (confirmation bias, sunk cost, anchoring, optimism bias) or avoidance behavior.
4. "acknowledgment" - The reflection is thoughtful and complete. Simply acknowledge it.

Respond with ONLY the category name, nothing else.

Founder text: {text}
Context: {context}
"""

    SOCRATIC_PROMPT = """You are a strategic thinking partner for a founder.
The founder wrote the following reflection that could use deeper exploration:

"{text}"

Ask ONE incisive Socratic question that:
- Goes beneath the surface observation
- Challenges an unstated assumption
- Connects to potential second-order consequences
- Is concise (under 30 words)

Do not be generic. Be specific to what they wrote."""

    RAG_RESPONSE_PROMPT = """You are a strategic thinking partner for a founder.
The founder wrote: "{text}"

Based on the following relevant excerpts from strategic thinking literature:
{context}

Recommend the most relevant mental model or framework for their current situation.
Be specific about HOW to apply the framework to their situation. Keep it under 150 words."""

    async def classify(self, text: str, context: dict = None) -> str:
        """Classify a FounderEvent into a response category."""
        provider = get_llm_provider()

        try:
            prompt = self.CLASSIFICATION_PROMPT.format(
                text=text,
                context=str(context or {}),
            )
            response = await provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.1,
            )
            category = response.strip().lower()

            valid_categories = ["rag_query", "clarifying_question", "pattern_alert", "acknowledgment"]
            if category in valid_categories:
                return category
            return "acknowledgment"
        except Exception as e:
            logger.error(f"Classification failed: {e}")
            return "acknowledgment"

    async def generate_response(self, text: str, category: str, rag_context: str = "") -> str:
        """Generate the appropriate response based on classification."""
        provider = get_llm_provider()

        try:
            if category == "clarifying_question":
                prompt = self.SOCRATIC_PROMPT.format(text=text)
            elif category == "rag_query":
                prompt = self.RAG_RESPONSE_PROMPT.format(text=text, context=rag_context)
            elif category == "pattern_alert":
                prompt = f"""Analyze this founder reflection for cognitive biases or avoidance patterns.
Be direct but constructive. Name the specific bias. Keep it under 100 words.

"{text}" """
            else:
                return "Noted. This reflection has been added to your growth journal."

            response = await provider.chat(
                [{"role": "user", "content": prompt}],
                temperature=0.3,
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Response generation failed: {e}")
            return "Your reflection has been recorded."


# Singleton
inference_router = InferenceRouter()
