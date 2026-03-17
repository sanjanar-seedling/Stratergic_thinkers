"""Personalized Inference Router.

Routes inference requests to either:
1. Base LLM (for new users)
2. Personalized LoRA adapter (for users with enough data)

Automatically triggers LoRA training when user has sufficient data.
"""

import logging
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FounderEvent, User
from app.core.llm_provider import get_llm_provider
from app.services.lora_personalizer import LoRAPersonalizer

logger = logging.getLogger(__name__)


class PersonalizedInferenceRouter:
    """Routes inference to personalized or base model."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.base_llm = get_llm_provider()
        self.lora_personalizer = LoRAPersonalizer()
        self.min_events_for_personalization = 100

    async def should_personalize(
        self,
        user_id: UUID,
    ) -> bool:
        """Check if user has enough data for personalization."""
        # Count user's events
        result = await self.db.execute(
            select(func.count(FounderEvent.id)).where(FounderEvent.user_id == user_id)
        )
        event_count = result.scalar()

        return event_count >= self.min_events_for_personalization

    async def has_trained_adapter(
        self,
        user_id: UUID,
    ) -> bool:
        """Check if user has a trained LoRA adapter."""
        adapter_path = self.lora_personalizer.output_dir / f"user_{user_id}"
        return adapter_path.exists()

    async def trigger_personalization_training(
        self,
        user_id: UUID,
    ) -> Optional[str]:
        """Trigger LoRA training for a user.
        
        Returns:
            Path to adapter if successful, None otherwise
        """
        logger.info(f"Triggering personalization training for user {user_id}")

        # Fetch user's events
        result = await self.db.execute(
            select(FounderEvent)
            .where(FounderEvent.user_id == user_id)
            .order_by(FounderEvent.created_at.desc())
            .limit(500)  # Use most recent 500 events
        )
        events = result.scalars().all()

        # Convert to dict format
        event_dicts = [
            {
                "event_type": e.event_type.value,
                "text": e.anonymized_text or "[encrypted]",
                "created_at": e.created_at.isoformat(),
            }
            for e in events
        ]

        # Prepare training data
        dataset = self.lora_personalizer.prepare_training_data(event_dicts)
        if not dataset:
            logger.warning(f"Insufficient data for user {user_id}")
            return None

        # Train LoRA adapter
        try:
            adapter_path = self.lora_personalizer.train_lora(
                user_id=user_id,
                dataset=dataset,
                num_epochs=3,
            )
            logger.info(f"Personalization training complete: {adapter_path}")
            return adapter_path
        except Exception as e:
            logger.error(f"Personalization training failed: {e}")
            return None

    async def generate(
        self,
        user_id: UUID,
        messages: list[dict],
        temperature: float = 0.3,
        use_personalization: bool = True,
    ) -> str:
        """Generate response using personalized or base model.
        
        Args:
            user_id: User ID
            messages: Chat messages
            temperature: Sampling temperature
            use_personalization: Whether to use personalized model if available
        
        Returns:
            Generated response
        """
        # Check if personalization is available and enabled
        if use_personalization:
            has_adapter = await self.has_trained_adapter(user_id)

            if has_adapter:
                logger.info(f"Using personalized model for user {user_id}")
                try:
                    # Extract instruction and input from messages
                    # Simplified: assumes last message is user input
                    last_message = messages[-1]["content"]
                    instruction = "Respond to this reflection:"

                    response = self.lora_personalizer.generate_personalized_response(
                        user_id=user_id,
                        instruction=instruction,
                        input_text=last_message,
                    )
                    return response
                except Exception as e:
                    logger.error(f"Personalized inference failed: {e}")
                    logger.info("Falling back to base model")

            else:
                # Check if we should trigger training
                should_train = await self.should_personalize(user_id)
                if should_train:
                    logger.info(f"User {user_id} has enough data for personalization")
                    # Trigger async training via Redis task queue (don't block current request)
                    try:
                        import redis as redis_lib
                        from datetime import datetime
                        redis_client = redis_lib.from_url("redis://localhost:6379", decode_responses=True)
                        redis_client.xadd(
                            "personalization_tasks",
                            {"user_id": user_id, "action": "train_lora", "timestamp": str(datetime.utcnow())}
                        )
                        logger.info(f"Personalization training task queued for user {user_id}")
                    except Exception as e:
                        logger.warning(f"Failed to queue personalization training: {e}")

        # Use base model
        logger.info(f"Using base model for user {user_id}")
        response = await self.base_llm.chat(messages, temperature)
        return response


if __name__ == "__main__":
    import asyncio
    from app.core.database import get_db

    async def test_router():
        async for db in get_db():
            router = PersonalizedInferenceRouter(db)

            # Example: Generate response
            # response = await router.generate(
            #     user_id=UUID("..."),
            #     messages=[
            #         {"role": "user", "content": "I'm feeling stuck on this decision..."}
            #     ],
            # )
            # print(response)

            break

    asyncio.run(test_router())
