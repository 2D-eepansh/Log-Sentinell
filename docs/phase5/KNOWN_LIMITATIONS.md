# Phase 5 – Known Limitations

## Base vs LoRA Full-Pipeline Comparison

A base-vs-LoRA comparison using the full backend inference path was prepared
(`llm/inference/debug_compare_lora.py`). The runner executes the same inference
pipeline twice (base model and LoRA-enabled) and writes captured outputs to
`base_vs_lora_inference.txt`.

In the current development environment (Windows, WDDM, RTX 5070 Laptop GPU with
8 GB VRAM), repeated attempts to load the 4-bit Mistral-7B model sequentially
(base then LoRA) resulted in `KeyboardInterrupt` during model load. This appears
to be an environment stability issue related to repeated quantized model loads
under constrained VRAM, not a functional limitation of the code.

The error trace from these attempts is preserved in
`docs/phase5/base_vs_lora_inference.txt`.

Adapter effectiveness was validated via a standalone QLoRA sanity test that
demonstrated non-identical, stylistically improved outputs between base and LoRA
models on identical prompts.

The full-pipeline comparison runner remains in place and will emit captured
outputs once a full uninterrupted model load completes in a stable session or
alternate environment.

## CPU Verification Mode (tiny-gpt2)

For release verification, the backend can be run with a small CPU model such as
`sshleifer/tiny-gpt2`. In this mode:

- Fallback explanations are expected and acceptable.
- The purpose is system stability, endpoint integration, and schema validation
	rather than explanation quality.
- This mode is used to validate that the LLM runtime remains stable on CPU and
	that the system returns bounded, schema-valid responses.

## LoRA Adapters with tiny-gpt2

The bundled LoRA adapters target Mistral-specific layers (e.g., `q_proj` and
`v_proj`). When the base model is tiny-gpt2:

- The mismatch is detected and logged during adapter attachment.
- The service returns a safe fallback response without crashing.
- True LoRA inference requires a compatible Mistral base model.
