"""
Adapter loading and swapping utilities.

Keeps base model weights unchanged; adapters are loaded separately and can be
activated or disabled without affecting architecture.
"""

from __future__ import annotations

from typing import Optional

from peft import PeftModel

from llm.mistral import MistralLocalModel


def load_lora_adapter(model: MistralLocalModel, adapter_path: str, name: str) -> None:
    """
    Load a LoRA adapter into the model under a given name.

    Base model weights remain unchanged.
    """

    if model._model is None or model._tokenizer is None:
        model.load()

    model._model = PeftModel.from_pretrained(model._model, adapter_path, adapter_name=name)


def set_active_adapter(model: MistralLocalModel, name: Optional[str]) -> None:
    """
    Activate a specific adapter by name, or disable adapters if name is None.
    """

    if model._model is None:
        model.load()

    if not hasattr(model._model, "set_adapter"):
        return

    if name is None:
        model._model.set_adapter("default")
    else:
        model._model.set_adapter(name)
