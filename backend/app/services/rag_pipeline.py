"""RAG Pipeline — Retrieval-Augmented Generation for the Strategic Framework Library.

Handles text chunking, embedding generation, pgvector storage, and similarity search
for the founder literature knowledge base.

Uses the swappable LLM provider for embeddings.
"""

import logging

from sqlalchemy import text

from app.core.llm_provider import get_llm_provider

logger = logging.getLogger(__name__)


def _format_vector(embedding: list[float]) -> str:
    """Format a Python list as a pgvector literal string, e.g. '[0.1,0.2,...]'."""
    return "[" + ",".join(str(v) for v in embedding) + "]"


class RAGPipeline:
    """Manages the Knowledge Base powered by pgvector."""

    def __init__(self, llm_provider=None):
        self._llm = llm_provider  # optional injected provider; falls back to global

    def _get_llm(self):
        return self._llm or get_llm_provider()

    def chunk_text(
        self,
        text_content: str,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
    ) -> list[str]:
        """Split text into overlapping chunks for embedding."""
        try:
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n\n", "\n", ". ", " ", ""],
            )
            return splitter.split_text(text_content)
        except ImportError:
            # Fallback simple chunking
            chunks = []
            for i in range(0, len(text_content), chunk_size - chunk_overlap):
                chunks.append(text_content[i:i + chunk_size])
            return chunks

    async def generate_embedding(self, text_content: str) -> list[float]:
        """Generate embedding vector for a text chunk using the configured provider."""
        return await self._get_llm().embed(text_content)

    async def similarity_search(
        self,
        query: str,
        db_session,
        limit: int = 5,
    ) -> list[dict]:
        """Find most similar knowledge chunks to the query using pgvector cosine similarity."""
        query_embedding = await self.generate_embedding(query)
        vec_str = _format_vector(query_embedding)

        result = await db_session.execute(
            text("""
                SELECT id, source_title, chunk_text,
                       1 - (embedding <=> CAST(:query_vec AS vector)) AS similarity
                FROM seedlings.knowledge_chunks
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> CAST(:query_vec AS vector)
                LIMIT :limit
            """),
            {"query_vec": vec_str, "limit": limit},
        )

        rows = result.fetchall()
        return [
            {
                "id": str(row.id),
                "source_title": row.source_title,
                "text": row.chunk_text,
                "similarity": float(row.similarity),
            }
            for row in rows
        ]

    async def ingest_document(
        self,
        text_content: str,
        source_title: str,
        source_author: str,
        db_session,
    ) -> int:
        """Chunk a document, embed it, and store in pgvector."""
        chunks = self.chunk_text(text_content)
        count = 0

        for i, chunk in enumerate(chunks):
            embedding = await self.generate_embedding(chunk)
            vec_str = _format_vector(embedding)

            await db_session.execute(
                text("""
                    INSERT INTO seedlings.knowledge_chunks
                        (id, source_title, source_author, chunk_text, chunk_index, embedding)
                    VALUES
                        (gen_random_uuid(), :title, :author, :chunk, :index, CAST(:embedding AS vector))
                """),
                {
                    "title": source_title,
                    "author": source_author,
                    "chunk": chunk,
                    "index": i,
                    "embedding": vec_str,
                },
            )
            count += 1

        await db_session.commit()
        logger.info(f"Ingested {count} chunks from '{source_title}'")
        return count

    async def suggest_frameworks_for_decision(self, context: str) -> dict:
        """Recommend strategic frameworks relevant to a given decision context."""
        llm = self._get_llm()

        prompt = f"""You are a strategic thinking advisor for startup founders.
Given the following decision context, recommend 3 relevant mental models or frameworks.

Context: {context}

For each framework provide:
1. Name (e.g. "Pre-Mortem Analysis", "First Principles Thinking")
2. Why it applies to this specific situation (2-3 sentences)
3. A concrete question the founder should ask using this framework

Return as a structured list."""

        response_text = await llm.chat(
            messages=[{"role": "user", "content": prompt}],
            system="You are an expert advisor on decision-making frameworks and mental models.",
        )

        # Built-in framework library for fallback / enrichment
        builtin_frameworks = _BUILTIN_FRAMEWORKS

        # Parse LLM response to extract framework names mentioned
        recommendations = []
        for fw in builtin_frameworks:
            if fw["name"].lower() in response_text.lower():
                recommendations.append({
                    "framework": fw,
                    "relevance_score": 0.85,
                    "reasoning": response_text,
                })
            if len(recommendations) >= 3:
                break

        # If LLM didn't match any known frameworks, return top 3 built-ins
        if not recommendations:
            recommendations = [
                {"framework": fw, "relevance_score": 0.7, "reasoning": response_text}
                for fw in builtin_frameworks[:3]
            ]

        return {"recommendations": recommendations, "llm_analysis": response_text}


# ── Built-in Strategic Framework Library ──────────────────────────────────────

_BUILTIN_FRAMEWORKS = [
    {
        "id": "first-principles",
        "name": "First Principles Thinking",
        "description": "Break down a problem to its fundamental truths, then reason up from there instead of reasoning by analogy.",
        "source": "Elon Musk / Aristotle",
        "category": "decision_making",
        "when_to_use": "When you feel constrained by conventional wisdom or industry norms.",
        "example": "Instead of 'How do we reduce battery cost?' ask 'What are batteries made of and what do those materials cost on commodity markets?'",
    },
    {
        "id": "reversible-irreversible",
        "name": "Reversible vs. Irreversible Decisions",
        "description": "Categorize decisions as one-way doors (irreversible, require caution) vs. two-way doors (reversible, bias toward action).",
        "source": "Jeff Bezos / Amazon",
        "category": "decision_making",
        "when_to_use": "When deciding how much analysis is needed before acting.",
        "example": "Hiring a VP is a two-way door — you can course correct. Raising a down-round is a one-way door. Treat them differently.",
    },
    {
        "id": "regret-minimization",
        "name": "Regret Minimization Framework",
        "description": "Project yourself to age 80 and ask which choice you would regret more. Optimize to minimize regret.",
        "source": "Jeff Bezos",
        "category": "decision_making",
        "when_to_use": "For major life and business decisions where you are torn between safety and a bold bet.",
        "example": "Will I regret NOT starting this company when I am 80? If yes, the expected regret of inaction exceeds the risk of action.",
    },
    {
        "id": "pre-mortem",
        "name": "Pre-Mortem Analysis",
        "description": "Imagine it is one year from now and the project has failed. Work backwards to identify what went wrong.",
        "source": "Gary Klein",
        "category": "decision_making",
        "when_to_use": "Before committing to a major initiative to surface hidden risks and assumptions.",
        "example": "It is Q4 2026. The pivot failed. What were the three root causes? Use that list to stress-test your plan now.",
    },
    {
        "id": "eisenhower-matrix",
        "name": "Eisenhower Matrix",
        "description": "Prioritize tasks by urgency and importance across four quadrants: Do, Schedule, Delegate, Eliminate.",
        "source": "Dwight D. Eisenhower",
        "category": "execution",
        "when_to_use": "When overwhelmed by tasks and unclear which ones deserve your personal attention.",
        "example": "Investor update = important + urgent → Do now. Process documentation = important + not urgent → Schedule.",
    },
    {
        "id": "opportunity-cost",
        "name": "Opportunity Cost",
        "description": "Every choice forecloses alternatives. The true cost of a decision includes the value of the best foregone option.",
        "source": "Economics",
        "category": "decision_making",
        "when_to_use": "When evaluating resource allocation — time, money, or team bandwidth.",
        "example": "Building the mobile app costs 2 engineers for 3 months. The opportunity cost is what those engineers could build instead.",
    },
    {
        "id": "inversion",
        "name": "Inversion",
        "description": "Instead of asking 'How do I succeed?', ask 'What would guarantee failure?' Then avoid those things.",
        "source": "Charlie Munger",
        "category": "strategy",
        "when_to_use": "When you are stuck on a problem or want to pressure-test a strategy.",
        "example": "To win enterprise deals: invert → what kills enterprise deals? (slow legal, security concerns, no champion). Now fix those.",
    },
    {
        "id": "jobs-to-be-done",
        "name": "Jobs to Be Done",
        "description": "Customers hire products to do a job. Focus on the progress they are trying to make, not on product features.",
        "source": "Clayton Christensen",
        "category": "strategy",
        "when_to_use": "When defining product strategy, pricing, or go-to-market positioning.",
        "example": "Founders do not buy project management software — they hire it to reduce anxiety about what is falling through the cracks.",
    },
]


# Singleton
rag_pipeline = RAGPipeline()
