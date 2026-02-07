# Phase 5: LoRA Fine-Tuning

## SECTION 1: TRAINING DATASET

**Schema** (JSONL):
```json
{
  "incident": { "...": "Phase 3 Incident object" },
  "explanation": { "...": "Phase 4 Explanation object" }
}
```

**Data sources:**
- Curated incidents + explanations
- Synthetic incidents (clearly labeled and versioned)

**Example sample:**
```json
{"incident": {"incident_id": "inc-1", "service": "api", "start_time": "...", "end_time": "...", "anomalies": [], "metrics_summary": {"anomaly_count": 1, "feature_count": 1, "max_score": 0.7, "severity_counts": {}}, "log_patterns": [], "operational_context": []}, "explanation": {"incident_id": "inc-1", "summary": "Elevated error rate observed in the API service.", "probable_causes": ["error_rate_spike"], "supporting_evidence": ["service=api"], "confidence_score": 0.5, "recommended_next_steps": ["Inspect error and warning logs for the affected service"], "limitations": "Limited supporting evidence available."}}
```

## SECTION 2: LoRA CONFIGURATION

- Target modules: `q_proj`, `k_proj`, `v_proj`, `o_proj`
- Rank (`r`): 8
- Alpha: 16
- Dropout: 0.05

**Rationale:** Focus on attention projections only to keep base model unchanged and adapter size minimal.

## SECTION 3: TRAINING PIPELINE

- Frameworks: HuggingFace Transformers + PEFT
- Script: `llm/training/train_lora.py`
- Reproducibility: fixed seed, JSON config, deterministic preprocessing

## SECTION 4: MODEL ARTIFACTS

- Adapters are saved to `llm/artifacts/lora/`
- Base model weights remain unchanged
- Adapters can be loaded and swapped at inference time using `llm/training/adapters.py`

## SECTION 5: EVALUATION

- Compare before/after explanations for consistency and tone
- Ensure schema validation still passes
- Non-goals: improved reasoning beyond provided evidence

## SECTION 6: TESTS & SAFETY

- Training samples must validate against schema
- Inference output must still pass Phase 4 schema validation
- Adapters can be disabled instantly for rollback
