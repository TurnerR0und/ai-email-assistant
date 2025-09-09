import json
from pathlib import Path
from collections import Counter
import asyncio
from sklearn.metrics import confusion_matrix, classification_report

# Import your classifier
from app.services.classifier import classify_ticket

# Path to your synthetic tickets file
DATA_PATH = Path("./challengetickets.jsonl")

# 1. Load up to 50 tickets
tickets = []
with open(DATA_PATH, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i >= 50:
            break
        obj = json.loads(line)
        # Change this if your ground truth field has a different name
        tickets.append({
            "subject": obj["subject"],
            "body": obj["body"],
            "true_category": obj.get("category") or obj.get("label") or "unknown"
        })

# 2. Classify all tickets
async def classify_all(tickets):
    results = []
    for t in tickets:
        pred = await classify_ticket(t['subject'], t['body'])
        results.append(pred)
    return results


predicted_categories = asyncio.run(classify_all(tickets))

# 3. Gather results
true_categories = [t["true_category"] for t in tickets]

# 4. Print confusion matrix and report
print("Classification Report:")
print(classification_report(true_categories, predicted_categories))

print("Confusion Matrix:")
print(confusion_matrix(true_categories, predicted_categories))

# 5. (Optional) Print mismatches
print("\nExamples of mismatches:")
for i, (true_cat, pred_cat, t) in enumerate(zip(true_categories, predicted_categories, tickets)):
    if true_cat != pred_cat:
        print(f"[{i}] Subject: {t['subject']}")
        print(f"    Body: {t['body']}")
        print(f"    True: {true_cat} | Predicted: {pred_cat}\n")

# 6. (Optional) Print category distribution
print("\nTrue Category Distribution:")
true_dist = Counter(true_categories)
for cat, count in true_dist.items():
    print(f"  {cat}: {count}")

print("\nPredicted Category Distribution:")
pred_dist = Counter(predicted_categories)
for cat, count in pred_dist.items():
    print(f"  {cat}: {count}")
