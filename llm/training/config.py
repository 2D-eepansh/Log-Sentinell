"""
Training configuration for LoRA fine-tuning.

Conservative defaults prioritize stability and avoid overfitting.
"""

from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


class TrainingConfig(BaseModel):
    """
    LoRA training configuration.

    Notes:
    - target_modules restricted to attention projections for parameter efficiency.
    - low learning rate and small epochs reduce overfitting risk.
    - max_seq_length caps prompt + output length for memory control.
    """

    model_path: str = Field(..., description="Local filesystem path to base model")
    dataset_path: str = Field(..., description="Path to JSONL training data")
    output_dir: str = Field("llm/artifacts/lora", description="Adapter output dir")

    seed: int = Field(42, ge=0)
    num_train_epochs: int = Field(3, ge=1, le=10)
    per_device_train_batch_size: int = Field(1, ge=1, le=16)
    gradient_accumulation_steps: int = Field(8, ge=1, le=64)
    learning_rate: float = Field(2e-5, gt=0.0, le=1e-3)
    weight_decay: float = Field(0.01, ge=0.0, le=0.1)
    warmup_steps: int = Field(10, ge=0)

    max_seq_length: int = Field(1536, ge=256, le=4096)

    lora_r: int = Field(8, ge=2, le=64)
    lora_alpha: int = Field(16, ge=4, le=128)
    lora_dropout: float = Field(0.05, ge=0.0, le=0.5)
    target_modules: List[str] = Field(
        default_factory=lambda: ["q_proj", "k_proj", "v_proj", "o_proj"]
    )
