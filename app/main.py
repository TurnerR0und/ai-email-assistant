from fastapi import FastAPI
from contextlib import asynccontextmanager
import asyncio
from app.routers import tickets
from app.routers import health
from app.logging_config import setup_logging, log_writer

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
    # install logging with async DB sink
    app.state.log_queue = asyncio.Queue(maxsize=1000)
    setup_logging(queue=app.state.log_queue)
    app.state.log_consumer = asyncio.create_task(log_writer(app.state.log_queue))
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
