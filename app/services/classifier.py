# app/services/classifier.py
from functools import lru_cache
import logging
import os
import time
from typing import Callable, Dict, Tuple

from prometheus_client import Counter, Histogram, Gauge
from opentelemetry import trace

logger = logging.getLogger(__name__)

# Metrics
CLASSIFIER_REQUESTS = Counter(
    "classifier_requests_total",
    "Total classification requests",
    labelnames=("backend", "label"),
)
CLASSIFIER_LATENCY = Histogram(
    "classifier_latency_seconds",
    "Classification latency in seconds",
    labelnames=("backend",),
)
CLASSIFIER_ERRORS = Counter(
    "classifier_errors_total",
    "Total classification errors",
    labelnames=("reason",),
)
GPU_SELECTED = Gauge(
    "gpu_selected",
    "Selected compute device for classifier (1 for selected)",
    labelnames=("device",),
)

# Global info for health/tracing
_MODEL_BACKEND = "unknown"
_MODEL_NAME = "unknown"
_MODEL_DEVICE = "cpu"


def _set_model_info(backend: str, model_name: str, device: str) -> None:
    global _MODEL_BACKEND, _MODEL_NAME, _MODEL_DEVICE
    _MODEL_BACKEND = backend
    _MODEL_NAME = model_name
    _MODEL_DEVICE = device
    try:
        # Set gauge for the selected device (cpu or gpu:0)
        GPU_SELECTED.labels(device=device).set(1)
    except Exception:
        pass


def get_model_info() -> Dict[str, str]:
    return {"backend": _MODEL_BACKEND, "model": _MODEL_NAME, "device": _MODEL_DEVICE}


CANDIDATE_LABELS = [
    "Billing",
    "Technical",
    "Account",
    "Complaint",
    "Feedback",
    "Refund",
    "Other",
]


def _mock_classifier() -> Callable[[str, Dict, bool], Dict[str, list]]:
    """Return a simple mock classifier that always predicts 'Refund'."""

    def _run(prompt: str, candidate_labels=None, multi_label: bool = False):  # type: ignore[override]
        label = "Refund" if (candidate_labels and "Refund" in candidate_labels) else (candidate_labels[0] if candidate_labels else "Other")
        return {"labels": [label], "scores": [0.99]}

    _set_model_info("mock", "mock-classifier", os.getenv("CUDA_VISIBLE_DEVICES", "") or "cpu")
    return _run


@lru_cache(maxsize=1)
def get_zero_shot_classifier():
    """Return a callable classifier. Supports mocking via env.

    If APP_MOCK_AI or MOCK_CLASSIFIER is set, provides a mock classifier to
    avoid heavy downloads/network access.
    """
    if os.getenv("APP_MOCK_AI") == "1" or os.getenv("MOCK_CLASSIFIER") == "1":
        logger.warning("Using MOCK classifier due to APP_MOCK_AI/MOCK_CLASSIFIER env flag.")
        return _mock_classifier()

    # Lazy imports so CI can run without installing heavy deps
    try:
        from transformers import pipeline  # type: ignore
    except Exception as e:
        logger.warning(f"Transformers not available, falling back to mock classifier: {e}")
        CLASSIFIER_ERRORS.labels(reason="import_transformers").inc()
        return _mock_classifier()

    # Torch optional
    try:
        import torch  # type: ignore
    except Exception:
        torch = None

    model_name = os.getenv("HF_MODEL", "facebook/bart-large-mnli")
    logger.warning(f"Initializing zero-shot pipeline: {model_name}")
    # Prefer GPU if available (device=0). Otherwise fall back to CPU (device=-1).
    device_index = -1
    device_str = "cpu"
    try:
        if (
            torch is not None
            and getattr(torch, "cuda", None) is not None
            and torch.cuda.is_available()
        ):
            device_index = 0
            device_str = "gpu:0"
            logger.warning("CUDA is available. Using GPU:0 for classification.")
        else:
            logger.warning("CUDA not available. Using CPU for classification.")
    except Exception:
        # Be safe in environments without CUDA
        device_index = -1
        device_str = "cpu"

    try:
        classifier = pipeline(
            "zero-shot-classification",
            model=model_name,
            device=device_index,
        )
        _set_model_info("hf", model_name, device_str)
        logger.warning(f"Zero-shot pipeline ready on device {device_index}.")
        return classifier
    except Exception as e:
        logger.error(f"ERROR initializing zero-shot pipeline: {e}", exc_info=True)
        CLASSIFIER_ERRORS.labels(reason="init_failed").inc()
        return _mock_classifier()


async def classify_ticket(subject: str, body: str) -> str:
    tracer = trace.get_tracer(__name__)
    info = get_model_info()

    prompt = (
        f"Subject: {subject}\n"
        f"Body: {body}\n"
        "You are an expert support agent categorizing issues. Please classify this customer support message as one of: "
        "Billing, Technical, Account, Complaint, Feedback, Refund, Other."
        "Only choose one label from this list."
    )

    classifier = get_zero_shot_classifier()

    logger.warning(f"Classifying ticket with subject: {subject[:30]}...")
    start = time.perf_counter()
    try:
        result = classifier(
            prompt,
            candidate_labels=CANDIDATE_LABELS,
            multi_label=False,
        )
        latency = time.perf_counter() - start
        label = result["labels"][0]
        # Metrics
        CLASSIFIER_LATENCY.labels(info.get("backend", "unknown")).observe(latency)
        CLASSIFIER_REQUESTS.labels(info.get("backend", "unknown"), label).inc()
        # Tracing
        with tracer.start_as_current_span("classify_ticket") as span:
            span.set_attribute("classifier.backend", info.get("backend", "unknown"))
            span.set_attribute("classifier.model", info.get("model", "unknown"))
            span.set_attribute("classifier.device", info.get("device", "cpu"))
            span.set_attribute("latency_ms", int(latency * 1000))
            span.set_attribute("label", label)
        logger.warning(f"Classification result: {label}")
        return label
    except Exception as e:
        CLASSIFIER_ERRORS.labels(reason="inference_error").inc()
        logger.error(f"ERROR during classification: {e}", exc_info=True)
        # Return a safe fallback
        return "Other"
