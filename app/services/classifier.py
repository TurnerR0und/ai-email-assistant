from functools import lru_cache
from transformers import pipeline

CANDIDATE_LABELS = [
    "Billing",
    "Technical",
    "Account",
    "Complaint",
    "Feedback",
    "Refund",
    "Other"
]

@lru_cache(maxsize=1)
def get_zero_shot_classifier():
    # Load the pipeline once per process (memory cache)
    return pipeline("zero-shot-classification", model="facebook/bart-large-mnli", from_flax=True)

async def classify_ticket(subject: str, body: str) -> str:
    prompt = (
        f"Subject: {subject}\n"
        f"Body: {body}\n"
        "You are an expert support agent categorizing issues. Please classify this customer support message as one of: "
        "Billing, Technical, Account, Complaint, Feedback, Refund, Other."
        "Only choose one label from this list."
    )
    classifier = get_zero_shot_classifier()
    result = classifier(
        prompt,
        candidate_labels=CANDIDATE_LABELS,
        multi_label=False
    )
    return result["labels"][0]
