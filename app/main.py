from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.routers import tickets
from app.logging_config import setup_logging

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
    setup_logging()
    # OpenTelemetry: Set up tracing *here* (if any context needs app)
    yield

app = FastAPI(lifespan=lifespan)

# Routers come first
app.include_router(tickets.router, prefix="/tickets", tags=["tickets"])

# Now instrument your app for telemetry & metrics
# OpenTelemetry tracing
provider = TracerProvider()
processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4318/v1/traces"))
provider.add_span_processor(processor)
trace.set_tracer_provider(provider)
FastAPIInstrumentor.instrument_app(app)

# Prometheus metrics
instrumentator = Instrumentator()
instrumentator.instrument(app).expose(app, endpoint="/metrics")
