# app/services/classifier.py
from functools import lru_cache
from transformers import pipeline
import logging
import os
try:
    import torch
except Exception:  # torch may not import in some minimal envs
    torch = None

logger = logging.getLogger(__name__)

CANDIDATE_LABELS = [
    "Billing", "Technical", "Account", "Complaint", "Feedback", "Refund", "Other"
]

@lru_cache(maxsize=1)
def get_zero_shot_classifier():
    model_name = "facebook/bart-large-mnli"
    logger.warning(f"Initializing zero-shot pipeline: {model_name}")
    # Prefer GPU if available (device=0). Otherwise fall back to CPU (device=-1).
    device = -1
    if torch is not None and getattr(torch, "cuda", None) is not None and torch.cuda.is_available():
        device = 0
        logger.warning("CUDA is available. Using GPU:0 for classification.")
    else:
        logger.warning("CUDA not available. Using CPU for classification.")
    try:
        classifier = pipeline(
            "zero-shot-classification",
            model=model_name,
            device=device,
        )
        logger.warning(f"Zero-shot pipeline ready on device {device}.")
        return classifier
    except Exception as e:
        logger.error(f"ERROR initializing zero-shot pipeline: {e}", exc_info=True)
        raise

async def classify_ticket(subject: str, body: str) -> str:
    prompt = (
        f"Subject: {subject}\n"
        f"Body: {body}\n"
        "You are an expert support agent categorizing issues. Please classify this customer support message as one of: "
        "Billing, Technical, Account, Complaint, Feedback, Refund, Other."
        "Only choose one label from this list."
    )
    # This call will now trigger the simplified get_zero_shot_classifier
    classifier = get_zero_shot_classifier()
    
    logger.warning(f"Classifying ticket with subject: {subject[:30]}...") # Log snippet
    result = classifier(
        prompt,
        candidate_labels=CANDIDATE_LABELS,
        multi_label=False
    )
    logger.warning(f"Classification result: {result['labels'][0]}")
    return result["labels"][0]
