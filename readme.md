AI Email Support Assistant

An open, modular support ticket system with AI-powered classification and (soon) response automation.Built with FastAPI, PostgreSQL, and Hugging Face transformers.Designed for hands-on learning, extensibility, and real-world MLOps practice.

🚀 Project Overview

This project is an end-to-end customer support platform that:

Receives and stores support tickets in a PostgreSQL database

Automatically classifies tickets by type (Billing, Technical, Account, Complaint, Feedback, Refund, Other) using zero-shot LLMs

(Next Milestone) Will generate automated response drafts using OpenAI or Hugging Face models

Provides a test/evaluation pipeline for measuring classification accuracy on synthetic and real-world tickets

🛠️ Tech Stack

FastAPI (async web API)

SQLAlchemy (async ORM)

PostgreSQL (Dockerized)

Alembic (migrations)

Pydantic v2 (validation)

Hugging Face Transformers (facebook/bart-large-mnli for zero-shot classification)

OpenAI API (optionally for ticket generation and LLMs)

httpie (for API testing)

Uvicorn (dev server)

Python 3.10+

📂 Code Structure

aiemailassistant/
│
├── app/
│   ├── main.py                # FastAPI entrypoint
│   ├── routers/
│   │   └── tickets.py         # API endpoints for ticket CRUD
│   ├── db/
│   │   ├── models.py          # SQLAlchemy models
│   │   └── database.py        # Session, engine setup
│   ├── services/
│   │   └── classifier.py      # Zero-shot classification logic
│   ├── schemas.py             # Pydantic request/response schemas
│   └── ...
├── alembic/                   # Migrations
├── alembic.ini
├── docker-compose.yml
├── load_synthetic_tickets.py  # Synthetic ticket generation script
├── evaluate_classifier.py     # Ticket classification evaluation script
├── synthetic_tickets.jsonl    # Synthetic ticket data (labeled)
├── challenge_tickets.jsonl    # Ambiguous/realistic test tickets (labeled)
├── .env.example               # Sample environment variables
└── README.md

⚡ Usage

Setup

Install dependencies

pip install -r requirements.txt

Configure environment variables

Copy `.env.example` to `.env` and fill in secrets/keys as needed. Do not commit `.env` (it is gitignored). If a key was previously committed, rotate it.

Set up the database

Start Postgres (locally or with Docker Compose)

Run Alembic migrations:

alembic upgrade head

Run the App

uvicorn app.main:app --reload --reload-dir ./app

API docs will be available at http://localhost:8000/docs.

Health checks

- Liveness/DB: `GET /health` → `{ status: ok, db: up|down }`
- ML/GPU: `GET /health/ml` → `{ gpu_available: bool, gpu_count: int }`

Test the Classifier

http POST http://localhost:8000/tickets/ subject="I need a refund" body="I was double charged."

The category will be assigned by the LLM.

Evaluate Performance

python evaluate_classifier.py

Prints classification metrics for both synthetic and challenge datasets.

🔬 Model & ML Details

Classification: Uses Hugging Face facebook/bart-large-mnli zero-shot pipeline with custom prompt engineering.

Candidate labels:["Billing", "Technical", "Account", "Complaint", "Feedback", "Refund", "Other"]

Prompt:

Subject: ...
Body: ...
You are an expert support agent categorizing issues. Please classify this customer support message as one of: Billing, Technical, Account, Complaint, Feedback, Refund, Other. Only choose one label from this list.

GPU usage

- The classifier automatically uses GPU if `torch.cuda.is_available()` (device 0), else CPU.
- When running via Docker, ensure the container has GPU access (e.g., `docker run --gpus all ...` or configure Compose to request a GPU). Torch/Transformers will detect CUDA inside the container.

🧑‍💻 Roadmap

 ✅End-to-end async CRUD API with ticket storage

 ✅Zero-shot classifier integration

 ✅Evaluation notebook/script for real and synthetic tickets

 AI-powered response generation (OpenAI/Hugging Face, coming soon)

 Model monitoring, logging, and error handling improvements
 - Prometheus metrics for FastAPI and LLM latency
 - OpenTelemetry tracing via OTLP collector
 - Async DB-backed logging of app warnings/errors

 SetFit/few-shot/fine-tuned pipeline (future)

 CI/CD and Dockerization for deployment

📚 Learning Focus

This project is part of a personal LLM/AI learning track:

Building real AI apps from scratch (theory → practice)

Exploring MLOps, deployment, and open-source best practices

Progressively moving from zero-shot → few-shot → fine-tuned models

🙌 Contributions

Currently a solo project, but open to ideas, pull requests, or learning collabs!Feel free to fork, open issues, or suggest improvements.

License

MIT (see LICENSE)
