"""Pattern Recognition Engine — Cognitive bias detection and avoidance behavior flagging.

Runs scheduled analysis on 7-day windows of founder data to identify:
- Cognitive biases (anchoring, sunk cost, confirmation, optimism)
- Avoidance behaviors (consistently deferring specific topics)
- Over-optimization traps (perfecting instead of executing)
"""

import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class PatternEngine:
    """Identifies recurring cognitive patterns and biases."""

    ANALYSIS_PROMPT = """You are an expert cognitive analyst specializing in founder decision-making.

Analyze the following set of journal entries from the past 7 days and identify:

1. **Cognitive Biases**: Look for anchoring bias, confirmation bias, sunk cost fallacy, optimism bias, recency bias, survivorship bias.
2. **Avoidance Behaviors**: Topics that are mentioned repeatedly but never acted upon.
3. **Over-Optimization Traps**: Signs of perfectionism blocking execution.
4. **Consistency Checks**: Contradictions between stated values/priorities and actual behaviors.

Entries:
{entries}

Calendar context (time allocation):
{calendar_context}

For each finding, provide:
- bias_type: name of the pattern
- description: specific evidence from the entries
- severity: "low", "medium", or "high"

Respond in JSON format: [{{"bias_type": "...", "description": "...", "severity": "..."}}]
If no biases are detected, return an empty array: []"""

    def __init__(self):
        self._llm = None

    def _get_llm(self):
        if self._llm is None:
            try:
                from langchain_openai import ChatOpenAI
                self._llm = ChatOpenAI(model="gpt-4o-mini", temperature=0.2)
            except Exception as e:
                logger.warning(f"LLM not available for pattern analysis: {e}")
        return self._llm

    async def analyze_week(
        self,
        entries: list[dict],
        calendar_context: dict = None,
    ) -> list[dict]:
        """Analyze a week's worth of entries for cognitive biases."""
        llm = self._get_llm()
        if llm is None:
            logger.info("Pattern analysis skipped — LLM not available")
            return []

        try:
            import json
            from langchain.schema import HumanMessage

            entries_text = "\n\n".join([
                f"[{e.get('created_at', 'unknown')}] ({e.get('source', 'journal')}): {e.get('text', '')}"
                for e in entries
            ])

            prompt = self.ANALYSIS_PROMPT.format(
                entries=entries_text,
                calendar_context=str(calendar_context or "No calendar data available"),
            )

            response = await llm.ainvoke([HumanMessage(content=prompt)])
            content = response.content.strip()

            # Extract JSON from response
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            findings = json.loads(content)
            logger.info(f"Pattern analysis found {len(findings)} biases")
            return findings

        except Exception as e:
            logger.error(f"Pattern analysis failed: {e}")
            return []

    def detect_avoidance(self, entries: list[dict], threshold: int = 3) -> list[dict]:
        """Simple heuristic: find topics mentioned repeatedly without action."""
        from collections import Counter

        # Extract key phrases (simplified — in production use NLP)
        word_freq = Counter()
        action_words = {"decided", "will", "done", "completed", "shipped", "launched", "hired", "fired"}

        for entry in entries:
            text = entry.get("text", "").lower()
            has_action = any(w in text for w in action_words)

            # Look for repeated noun phrases (simplified)
            words = text.split()
            for i in range(len(words) - 1):
                bigram = f"{words[i]} {words[i+1]}"
                if not has_action and len(bigram) > 5:
                    word_freq[bigram] += 1

        avoidance_topics = [
            {"topic": topic, "mentions": count, "severity": "high" if count >= 5 else "medium"}
            for topic, count in word_freq.most_common(5)
            if count >= threshold
        ]

        return avoidance_topics


# Singleton
pattern_engine = PatternEngine()
