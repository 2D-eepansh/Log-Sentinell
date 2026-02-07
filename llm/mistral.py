"""
Local Mistral model loader and inference wrapper.

Offline-only: uses local_files_only=True by default.
"""

from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Optional

from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

from .config import LLMConfig, LORA_PATH, USE_LORA

logger = logging.getLogger("llm")


@dataclass
class MistralLocalModel:
    """
    Local Mistral model wrapper.

    Provides deterministic generation with temperature=0.0 and do_sample=False.
    """

    config: LLMConfig
    _tokenizer: Optional[AutoTokenizer] = None
    _model: Optional[AutoModelForCausalLM] = None

    def load(self) -> None:
        if self._model is not None and self._tokenizer is not None:
            return
        try:
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:
            device = "cpu"

        logger.info("Loading base model from %s (local_files_only=%s, device=%s)", self.config.model_path, self.config.local_files_only, device)
        self._tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_path, local_files_only=self.config.local_files_only
        )
        self._model = AutoModelForCausalLM.from_pretrained(
            self.config.model_path, local_files_only=self.config.local_files_only
        )
        logger.info("Base model loaded successfully")
        if USE_LORA:
            logger.info("Attaching LoRA adapter from %s", LORA_PATH)
            self._model = PeftModel.from_pretrained(
                self._model,
                LORA_PATH,
                is_trainable=False,
                local_files_only=self.config.local_files_only,
            )
            logger.info("LoRA adapter attached")
        self._model.eval()

    def generate(self, prompt: str) -> str:
        if self._model is None or self._tokenizer is None:
            self.load()

        max_positions = getattr(self._model.config, "n_positions", None) or getattr(
            self._model.config, "max_position_embeddings", None
        )
        model_max_length = self._tokenizer.model_max_length
        if max_positions:
            max_length = min(model_max_length, max_positions)
        else:
            max_length = model_max_length

        max_input_tokens = max_length - self.config.max_new_tokens
        if max_input_tokens < 1:
            max_input_tokens = max_length

        inputs = self._tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=max_input_tokens,
        )
        max_available = max_length - inputs["input_ids"].shape[1]
        max_new_tokens = max(1, min(self.config.max_new_tokens, max_available))
        output_ids = self._model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            repetition_penalty=self.config.repetition_penalty,
            do_sample=False,
            eos_token_id=self._tokenizer.eos_token_id,
        )
        decoded = self._tokenizer.decode(output_ids[0], skip_special_tokens=True)
        return decoded
