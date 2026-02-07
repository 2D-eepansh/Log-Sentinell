"""
Configuration for local LLM inference.

All settings are deterministic and safe for offline use.
"""

from __future__ import annotations

import os

from pathlib import Path

from pydantic import BaseModel, Field


class LLMConfig(BaseModel):
    """
    Configuration for the Mistral local model.

    Notes:
    - model_path must point to a local directory (no remote fetch).
    - temperature is 0.0 to reduce variability.
    - do_sample is disabled for deterministic output shape.
    """

    model_path: str = Field(..., description="Local filesystem path to Mistral model")
    max_new_tokens: int = Field(512, ge=64, le=2048)
    temperature: float = Field(0.0, ge=0.0, le=1.0)
    top_p: float = Field(0.9, ge=0.0, le=1.0)
    repetition_penalty: float = Field(1.05, ge=1.0, le=2.0)
    local_files_only: bool = False

    def model_post_init(self, __context: object) -> None:
        path = Path(self.model_path)
        if path.exists():
            self.local_files_only = True


def _parse_bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


# LoRA inference toggle
USE_LORA = _parse_bool(os.getenv("USE_LORA"), False)
LORA_PATH = os.getenv("LORA_PATH", "llm/models/lora")
