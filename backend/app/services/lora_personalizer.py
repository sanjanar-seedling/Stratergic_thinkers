"""LoRA Fine-Tuning for Personalized AI.

Fine-tunes a small LoRA adapter on the founder's writing style and thinking patterns.
This enables:
1. Personalized intervention phrasing
2. Better understanding of founder's unique context
3. More relevant framework recommendations
4. Adaptive questioning style

Uses QLoRA (Quantized LoRA) for efficient training on consumer GPUs.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from uuid import UUID

import torch
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
    Trainer,
)
from datasets import Dataset

logger = logging.getLogger(__name__)


class LoRAPersonalizer:
    """Fine-tunes LoRA adapters for personalized AI."""

    def __init__(
        self,
        base_model: str = "mistralai/Mistral-7B-Instruct-v0.2",
        output_dir: str = "./lora_adapters",
    ):
        """Initialize LoRA personalizer.
        
        Args:
            base_model: HuggingFace model ID
            output_dir: Directory to save LoRA adapters
        """
        self.base_model = base_model
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def prepare_training_data(
        self,
        events: List[Dict],
        min_events: int = 50,
    ) -> Optional[Dataset]:
        """Prepare training data from founder events.
        
        Args:
            events: List of FounderEvent dicts
            min_events: Minimum number of events required for training
        
        Returns:
            HuggingFace Dataset or None if insufficient data
        """
        if len(events) < min_events:
            logger.warning(
                f"Insufficient data for training: {len(events)} events (need {min_events})"
            )
            return None

        # Create training examples
        training_examples = []

        for event in events:
            event_type = event.get("event_type")
            text = event.get("text", "")

            if not text:
                continue

            # Create different training formats based on event type
            if event_type == "reflection":
                # Format: reflection -> insight
                training_examples.append(
                    {
                        "instruction": "Reflect on this thought and extract key insights:",
                        "input": text,
                        "output": f"Key insight: {text[:200]}...",  # Simplified
                    }
                )

            elif event_type == "decision_record":
                # Format: decision -> framework suggestion
                training_examples.append(
                    {
                        "instruction": "What decision framework would be most helpful here?",
                        "input": text,
                        "output": "Consider using the Reversible vs. Irreversible Decisions framework.",
                    }
                )

            elif event_type == "weekly_review":
                # Format: review -> follow-up question
                training_examples.append(
                    {
                        "instruction": "Generate a thoughtful follow-up question:",
                        "input": text,
                        "output": "What would you do differently next week?",
                    }
                )

        if len(training_examples) < min_events:
            logger.warning(f"Only {len(training_examples)} valid training examples")
            return None

        # Convert to HuggingFace Dataset
        dataset = Dataset.from_list(training_examples)
        return dataset

    def format_prompt(
        self,
        instruction: str,
        input_text: str,
        output_text: Optional[str] = None,
    ) -> str:
        """Format training example as prompt.
        
        Uses Alpaca-style formatting.
        """
        prompt = f"""### Instruction:
{instruction}

### Input:
{input_text}

### Response:
"""
        if output_text:
            prompt += output_text

        return prompt

    def train_lora(
        self,
        user_id: UUID,
        dataset: Dataset,
        num_epochs: int = 3,
        learning_rate: float = 2e-4,
        batch_size: int = 4,
    ) -> str:
        """Train LoRA adapter on user's data.
        
        Args:
            user_id: User ID
            dataset: Training dataset
            num_epochs: Number of training epochs
            learning_rate: Learning rate
            batch_size: Batch size
        
        Returns:
            Path to saved adapter
        """
        logger.info(f"Starting LoRA training for user {user_id}")
        logger.info(f"Dataset size: {len(dataset)} examples")

        # QLoRA configuration (4-bit quantization)
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

        # Load base model
        logger.info(f"Loading base model: {self.base_model}")
        model = AutoModelForCausalLM.from_pretrained(
            self.base_model,
            quantization_config=bnb_config,
            device_map="auto",
            trust_remote_code=True,
        )

        # Prepare model for k-bit training
        model = prepare_model_for_kbit_training(model)

        # LoRA configuration
        lora_config = LoraConfig(
            r=16,  # LoRA rank
            lora_alpha=32,  # LoRA alpha
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],  # Attention layers
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
        )

        # Apply LoRA
        model = get_peft_model(model, lora_config)
        model.print_trainable_parameters()

        # Load tokenizer
        tokenizer = AutoTokenizer.from_pretrained(self.base_model)
        tokenizer.pad_token = tokenizer.eos_token

        # Tokenize dataset
        def tokenize_function(examples):
            prompts = [
                self.format_prompt(inst, inp, out)
                for inst, inp, out in zip(
                    examples["instruction"],
                    examples["input"],
                    examples["output"],
                )
            ]
            return tokenizer(
                prompts,
                truncation=True,
                max_length=512,
                padding="max_length",
            )

        tokenized_dataset = dataset.map(
            tokenize_function,
            batched=True,
            remove_columns=dataset.column_names,
        )

        # Training arguments
        adapter_path = self.output_dir / f"user_{user_id}"
        training_args = TrainingArguments(
            output_dir=str(adapter_path),
            num_train_epochs=num_epochs,
            per_device_train_batch_size=batch_size,
            gradient_accumulation_steps=4,
            learning_rate=learning_rate,
            fp16=True,
            logging_steps=10,
            save_strategy="epoch",
            optim="paged_adamw_8bit",
            warmup_steps=50,
        )

        # Trainer
        trainer = Trainer(
            model=model,
            args=training_args,
            train_dataset=tokenized_dataset,
            tokenizer=tokenizer,
        )

        # Train
        logger.info("Starting training...")
        trainer.train()

        # Save adapter
        logger.info(f"Saving adapter to {adapter_path}")
        model.save_pretrained(adapter_path)
        tokenizer.save_pretrained(adapter_path)

        # Save metadata
        metadata = {
            "user_id": str(user_id),
            "base_model": self.base_model,
            "training_date": datetime.utcnow().isoformat(),
            "num_examples": len(dataset),
            "num_epochs": num_epochs,
            "learning_rate": learning_rate,
        }
        with open(adapter_path / "metadata.json", "w") as f:
            json.dump(metadata, f, indent=2)

        logger.info(f"Training complete! Adapter saved to {adapter_path}")
        return str(adapter_path)

    def load_personalized_model(
        self,
        user_id: UUID,
    ):
        """Load a user's personalized LoRA adapter.
        
        Args:
            user_id: User ID
        
        Returns:
            (model, tokenizer)
        """
        adapter_path = self.output_dir / f"user_{user_id}"

        if not adapter_path.exists():
            raise ValueError(f"No adapter found for user {user_id}")

        logger.info(f"Loading personalized model from {adapter_path}")

        # Load base model with quantization
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

        model = AutoModelForCausalLM.from_pretrained(
            self.base_model,
            quantization_config=bnb_config,
            device_map="auto",
        )

        # Load LoRA adapter
        from peft import PeftModel

        model = PeftModel.from_pretrained(model, str(adapter_path))
        tokenizer = AutoTokenizer.from_pretrained(str(adapter_path))

        return model, tokenizer

    def generate_personalized_response(
        self,
        user_id: UUID,
        instruction: str,
        input_text: str,
        max_length: int = 256,
    ) -> str:
        """Generate a personalized response using the user's LoRA adapter.
        
        Args:
            user_id: User ID
            instruction: Instruction for the model
            input_text: Input text
            max_length: Maximum response length
        
        Returns:
            Generated response
        """
        model, tokenizer = self.load_personalized_model(user_id)

        # Format prompt
        prompt = self.format_prompt(instruction, input_text)

        # Tokenize
        inputs = tokenizer(prompt, return_tensors="pt").to(model.device)

        # Generate
        with torch.no_grad():
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_length,
                temperature=0.7,
                top_p=0.9,
                do_sample=True,
            )

        # Decode
        response = tokenizer.decode(outputs[0], skip_special_tokens=True)

        # Extract response (after "### Response:")
        if "### Response:" in response:
            response = response.split("### Response:")[1].strip()

        return response


if __name__ == "__main__":
    # Example usage
    personalizer = LoRAPersonalizer()

    # Prepare training data
    sample_events = [
        {
            "event_type": "reflection",
            "text": "Feeling overwhelmed with the product roadmap. Too many features, not enough focus.",
        },
        {
            "event_type": "decision_record",
            "text": "Decided to cut 3 features from Q2 roadmap to focus on core value prop.",
        },
        # ... more events
    ]

    # dataset = personalizer.prepare_training_data(sample_events)
    # if dataset:
    #     adapter_path = personalizer.train_lora(
    #         user_id=UUID("..."),
    #         dataset=dataset,
    #     )
    #     print(f"Adapter saved to: {adapter_path}")
