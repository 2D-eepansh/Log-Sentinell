"""
LoRA fine-tuning script for Mistral incident explanations.

This script performs parameter-efficient training only (LoRA adapters),
leaving base model weights unchanged.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Dict, List

import torch
from peft import LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, Trainer, TrainingArguments

from .config import TrainingConfig
from .dataset import build_training_prompt, format_completion, load_training_samples


@dataclass
class _TokenizedSample:
    input_ids: List[int]
    attention_mask: List[int]
    labels: List[int]


def _tokenize_sample(tokenizer, prompt: str, completion: str, max_length: int) -> _TokenizedSample:
    text = prompt + completion
    encoded = tokenizer(
        text,
        truncation=True,
        max_length=max_length,
        padding="max_length",
    )
    labels = encoded["input_ids"].copy()
    return _TokenizedSample(
        input_ids=encoded["input_ids"],
        attention_mask=encoded["attention_mask"],
        labels=labels,
    )


def _build_dataset(tokenizer, config: TrainingConfig) -> List[Dict[str, List[int]]]:
    samples = load_training_samples(config.dataset_path)
    dataset = []
    for sample in samples:
        prompt = build_training_prompt(sample)
        completion = format_completion(sample)
        tokenized = _tokenize_sample(tokenizer, prompt, completion, config.max_seq_length)
        dataset.append(
            {
                "input_ids": tokenized.input_ids,
                "attention_mask": tokenized.attention_mask,
                "labels": tokenized.labels,
            }
        )
    return dataset


def train_lora(config: TrainingConfig) -> None:
    """
    Run LoRA training and save adapters to output_dir.
    """

    torch.manual_seed(config.seed)

    tokenizer = AutoTokenizer.from_pretrained(config.model_path, local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(config.model_path, local_files_only=True)

    lora = LoraConfig(
        r=config.lora_r,
        lora_alpha=config.lora_alpha,
        target_modules=config.target_modules,
        lora_dropout=config.lora_dropout,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)

    train_dataset = _build_dataset(tokenizer, config)

    args = TrainingArguments(
        output_dir=config.output_dir,
        per_device_train_batch_size=config.per_device_train_batch_size,
        gradient_accumulation_steps=config.gradient_accumulation_steps,
        num_train_epochs=config.num_train_epochs,
        learning_rate=config.learning_rate,
        weight_decay=config.weight_decay,
        warmup_steps=config.warmup_steps,
        logging_steps=10,
        save_steps=50,
        save_total_limit=2,
        fp16=torch.cuda.is_available(),
        report_to=[],
    )

    trainer = Trainer(model=model, args=args, train_dataset=train_dataset)
    trainer.train()
    model.save_pretrained(config.output_dir)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="LoRA fine-tuning for Mistral")
    parser.add_argument("--config", required=True, help="Path to JSON config file")
    args = parser.parse_args()

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = TrainingConfig(**json.load(f))

    train_lora(cfg)
