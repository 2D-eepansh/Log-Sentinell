import random

import numpy as np
import torch
from datasets import load_dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig, TrainingArguments, Trainer
from peft import LoraConfig, get_peft_model

torch.manual_seed(42)
random.seed(42)
np.random.seed(42)

model_id = "mistralai/Mistral-7B-Instruct-v0.2"

bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=bnb_config,
    device_map="auto"
)

assert model.is_loaded_in_4bit, "Model is NOT in 4-bit mode"

lora_config = LoraConfig(
    r=8,
    lora_alpha=16,
    target_modules=["q_proj", "v_proj"],
    lora_dropout=0.05,
    bias="none",
    task_type="CAUSAL_LM"
)

model = get_peft_model(model, lora_config)
model.print_trainable_parameters()

dataset = load_dataset(
    "json",
    data_files={
        "train": "llm/training/datasets/phase5_incident_explanations/processed/train.jsonl",
        "validation": "llm/training/datasets/phase5_incident_explanations/processed/val.jsonl",
    }
)

def format_example(example):
    text = f"""<incident>
{example['input']}
</incident>

<explanation>
{example['output']}
</explanation>"""
    tokenized = tokenizer(text, truncation=True)
    tokenized["labels"] = tokenized["input_ids"].copy()
    return tokenized

tokenized = dataset.map(format_example, remove_columns=dataset["train"].column_names)

args = TrainingArguments(
    output_dir="llm/models/lora",
    per_device_train_batch_size=1,
    gradient_accumulation_steps=8,
    num_train_epochs=3,
    learning_rate=2e-4,
    fp16=True,
    logging_steps=10,
    save_strategy="epoch",
    report_to="none"
)

trainer = Trainer(
    model=model,
    args=args,
    train_dataset=tokenized["train"]
)

trainer.train()
model.save_pretrained("llm/models/lora")
