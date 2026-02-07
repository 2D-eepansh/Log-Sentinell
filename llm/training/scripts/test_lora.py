import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from peft import PeftModel

MODEL_ID = "mistralai/Mistral-7B-Instruct-v0.2"
LORA_PATH = "llm/models/lora"

prompt = """
You are given an incident context.

Incident:
Service: hdfs
Time window: 10:00–10:10
Log patterns:
- Connection reset by peer
- Timeout waiting for response

Metrics:
- Error rate: 3x baseline
- Latency p95: 2.4s

Explain the incident cautiously.
"""

# ---- Load base model (4-bit) ----
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)

tokenizer = AutoTokenizer.from_pretrained(MODEL_ID)

base_model = AutoModelForCausalLM.from_pretrained(
    MODEL_ID,
    quantization_config=bnb_config,
    device_map="auto"
)

# ---- Generate with base model ----
inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

with torch.no_grad():
    base_out = base_model.generate(
        **inputs,
        max_new_tokens=200,
        temperature=0.0,
        do_sample=False,
    )

print("\n================ BASE MODEL OUTPUT ================\n")
print(tokenizer.decode(base_out[0], skip_special_tokens=True))

# ---- Load LoRA adapter ----
lora_model = PeftModel.from_pretrained(base_model, LORA_PATH)

# ---- Generate with LoRA model ----
with torch.no_grad():
    lora_out = lora_model.generate(
        **inputs,
        max_new_tokens=200,
        temperature=0.0,
        do_sample=False,
    )

print("\n================ LORA MODEL OUTPUT ================\n")
print(tokenizer.decode(lora_out[0], skip_special_tokens=True))
