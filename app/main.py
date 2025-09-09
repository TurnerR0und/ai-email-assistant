from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
import os
from app.routers import tickets, inbound_email, health
from app.logging_config import setup_logging, log_writer
from app.services.classifier import (
    get_zero_shot_classifier,
    get_model_info,
    CANDIDATE_LABELS,
)

# OpenTelemetry imports
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

# Prometheus
from prometheus_fastapi_instrumentator import Instrumentator

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure DB schema exists before serving
    try:
        from app.db.database import engine
        from app.db.models import Base
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception:
        # Avoid failing startup in test/mock environments
        pass

    # install logging with async DB sink
    app.state.log_queue = asyncio.Queue(maxsize=1000)
    setup_logging(queue=app.state.log_queue)
    app.state.log_consumer = asyncio.create_task(log_writer(app.state.log_queue))
    # Warm ML model (eager load and run a tiny inference to fill caches)
    app.state.model_loaded = False
    app.state.model_backend = "unknown"
    app.state.model_name = "unknown"
    app.state.model_device = "cpu"
    try:
        classifier = get_zero_shot_classifier()
        # Record model info
        info = get_model_info()
        app.state.model_backend = info.get("backend", "unknown")
        app.state.model_name = info.get("model", "unknown")
        app.state.model_device = info.get("device", "cpu")
        # Tiny warmup (will be cheap with mock)
        _ = classifier(
            "Subject: warmup\nBody: test\n",
            candidate_labels=CANDIDATE_LABELS,
            multi_label=False,
        )
        app.state.model_loaded = True
    except Exception:
        app.state.model_loaded = False
    # OpenTelemetry: Set up tracing *here* (if any context needs app)
    try:
        yield
    finally:
        # graceful shutdown of log consumer
        try:
            await app.state.log_queue.put(None)
            await asyncio.wait_for(app.state.log_consumer, timeout=5)
        except Exception:
            pass

app = FastAPI(lifespan=lifespan)

# Routers come first
app.include_router(tickets.router, prefix="/tickets", tags=["tickets"])
app.include_router(health.router)
app.include_router(inbound_email.router, prefix="/email", tags=["email"]) # <--- INCLUDE NEW ROUTER

# Now instrument your app for telemetry & metrics
# OpenTelemetry tracing (disable in tests/CI by setting DISABLE_OTEL=1)
if os.getenv("DISABLE_OTEL", "0") != "1":
    provider = TracerProvider()
    processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4318/v1/traces"))
    provider.add_span_processor(processor)
    trace.set_tracer_provider(provider)
    FastAPIInstrumentor.instrument_app(app)

# Prometheus metrics
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app, endpoint="/metrics")

# Lightweight init for tests that import app without starting lifespan
if os.getenv("PYTEST_CURRENT_TEST") is not None and not hasattr(app.state, "log_queue"):
    try:
        app.state.log_queue = asyncio.Queue(maxsize=1000)
        setup_logging(queue=app.state.log_queue)
        app.state.log_consumer = asyncio.create_task(log_writer(app.state.log_queue))
    except Exception:
        pass
