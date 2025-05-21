# app/services/classifier.py
from functools import lru_cache
from transformers import pipeline
import logging

logger = logging.getLogger(__name__)

CANDIDATE_LABELS = [
    "Billing", "Technical", "Account", "Complaint", "Feedback", "Refund", "Other"
]

@lru_cache(maxsize=1)
def get_zero_shot_classifier():
    model_name = "facebook/bart-large-mnli"
    # Using logger.warning for higher visibility in logs during this test
    logger.warning(f"Attempting to initialize pipeline for model: {model_name} (defaulting to PyTorch)")
    try:
        # The pipeline should default to PyTorch since torch is installed.
        # We are removing any from_flax=True or explicit framework="pt" for this baseline test.
        # device=-1 for CPU. If you have a GPU and CUDA is set up in the container, you might use device=0.
        classifier = pipeline("zero-shot-classification", model=model_name, device=-1)
        logger.warning(f"Pipeline for {model_name} initialized successfully.")
        return classifier
    except Exception as e:
        logger.error(f"ERROR during pipeline initialization for {model_name}: {e}", exc_info=True)
        raise # Re-raise to see the error immediately

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
