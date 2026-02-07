import copy
import json
import os
import traceback
from datetime import datetime, timezone
from pathlib import Path

import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

import llm.config as llm_config
import llm.mistral as llm_mistral
from backend.llm_service import IncidentExplanationService
from llm.config import LLMConfig, LORA_PATH
from backend.incident.schema import Incident, LogPattern, MetricsSummary, OperationalEvent
from src.anomaly.schema import AnomalyEvent, AnomalySeverity, FeatureAnomaly

MODEL_PATH = os.environ.get("MODEL_PATH")

if MODEL_PATH:
    model_path = Path(MODEL_PATH)
else:
    hf_snapshot_root = (
        Path.home()
        / ".cache"
        / "huggingface"
        / "hub"
        / "models--mistralai--Mistral-7B-Instruct-v0.2"
        / "snapshots"
    )
    if hf_snapshot_root.exists():
        snapshots = sorted([p for p in hf_snapshot_root.iterdir() if p.is_dir()])
        model_path = snapshots[0] if snapshots else hf_snapshot_root
    else:
        model_path = hf_snapshot_root

if not model_path.exists():
    raise RuntimeError(
        "MODEL_PATH environment variable is required and must point to a local Mistral model directory"
    )


def build_incident() -> Incident:
    window_start = datetime(2025, 2, 7, 10, 0, tzinfo=timezone.utc)
    detected_at = datetime(2025, 2, 7, 10, 10, tzinfo=timezone.utc)

    anomaly = FeatureAnomaly(
        feature="error_rate",
        observed=0.12,
        baseline_mean=0.04,
        baseline_std=0.01,
        z_score=8.0,
        rate_change=2.0,
        score=0.85,
        severity=AnomalySeverity.HIGH,
        direction="high",
        suppressed=False,
    )

    event = AnomalyEvent(
        service="hdfs",
        window_start=window_start,
        detected_at=detected_at,
        severity=AnomalySeverity.HIGH,
        score=0.85,
        anomalies=[anomaly],
    )

    metrics_summary = MetricsSummary(
        anomaly_count=1,
        feature_count=1,
        max_score=0.85,
        severity_counts={AnomalySeverity.HIGH: 1},
    )

    return Incident(
        incident_id="inc-hdfs-2025-02-07-1000",
        service="hdfs",
        start_time=window_start,
        end_time=detected_at,
        anomalies=[event],
        metrics_summary=metrics_summary,
        log_patterns=[],
        operational_context=[],
    )


class _HFModelWrapper:
    def __init__(self, tokenizer, model, config: LLMConfig) -> None:
        self._tokenizer = tokenizer
        self._model = model
        self._config = config

    def generate(self, prompt: str) -> str:
        inputs = self._tokenizer(prompt, return_tensors="pt").to(self._model.device)
        output_ids = self._model.generate(
            **inputs,
            max_new_tokens=self._config.max_new_tokens,
            temperature=self._config.temperature,
            top_p=self._config.top_p,
            repetition_penalty=self._config.repetition_penalty,
            do_sample=False,
            eos_token_id=self._tokenizer.eos_token_id,
        )
        return self._tokenizer.decode(output_ids[0], skip_special_tokens=True)


def _load_base_model() -> tuple[AutoTokenizer, AutoModelForCausalLM]:
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.float16,
        bnb_4bit_use_double_quant=True,
    )
    tokenizer = AutoTokenizer.from_pretrained(str(model_path), local_files_only=True)
    model = AutoModelForCausalLM.from_pretrained(
        str(model_path),
        quantization_config=bnb_config,
        device_map="cuda",
        local_files_only=True,
    )
    model.eval()
    return tokenizer, model


def run_inference_with_model(
    use_lora: bool,
    incident: Incident,
    tokenizer: AutoTokenizer,
    base_model: AutoModelForCausalLM,
) -> dict:
    llm_config.USE_LORA = use_lora
    llm_mistral.USE_LORA = use_lora
    config = LLMConfig(model_path=str(model_path), max_new_tokens=64)

    model = base_model
    if use_lora:
        model = PeftModel.from_pretrained(
            base_model,
            LORA_PATH,
            is_trainable=False,
            local_files_only=True,
        )
        model.eval()

    wrapper = _HFModelWrapper(tokenizer, model, config)
    service = IncidentExplanationService(model=wrapper)
    explanation = service.explain(copy.deepcopy(incident))
    return explanation.model_dump()


def main() -> None:
    incident = build_incident()

    repo_root = Path(__file__).resolve().parents[2]
    evidence_path = repo_root / "docs/phase5/base_vs_lora_inference.txt"

    try:
        tokenizer, base_model = _load_base_model()
        base_output = run_inference_with_model(False, incident, tokenizer, base_model)
        base_text = "\n".join(
            [
                "=== BASE ===",
                json.dumps(base_output, indent=2, sort_keys=True),
                "",
            ]
        )
        print(base_text)
        evidence_path.write_text(base_text, encoding="utf-8")

        lora_output = run_inference_with_model(True, incident, tokenizer, base_model)
        lora_text = "\n".join(
            [
                "=== LORA ===",
                json.dumps(lora_output, indent=2, sort_keys=True),
                "",
            ]
        )
        print(lora_text)
        evidence_path.write_text(base_text + lora_text, encoding="utf-8")
    except BaseException:
        error_text = "\n".join(
            [
                "=== ERROR ===",
                traceback.format_exc(),
            ]
        )
        print(error_text)
        evidence_path.write_text(error_text, encoding="utf-8")
        raise


if __name__ == "__main__":
    main()
