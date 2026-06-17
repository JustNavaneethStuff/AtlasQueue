from __future__ import annotations

from atlasqueue.shared.config import Settings
from atlasqueue.shared.logging import get_logger

logger = get_logger(__name__)


def setup_telemetry(settings: Settings, service_name: str | None = None) -> None:
    if not settings.otel_exporter_otlp_endpoint:
        logger.info("OpenTelemetry exporter not configured, skipping setup")
        return

    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor

    resource = Resource.create({"service.name": service_name or settings.otel_service_name})
    provider = TracerProvider(resource=resource)
    exporter = OTLPSpanExporter(endpoint=settings.otel_exporter_otlp_endpoint, insecure=True)
    provider.add_span_processor(BatchSpanProcessor(exporter))
    trace.set_tracer_provider(provider)
    logger.info("OpenTelemetry configured for %s", service_name or settings.otel_service_name)


def instrument_fastapi(app: object) -> None:
    try:
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

        FastAPIInstrumentor.instrument_app(app)  # type: ignore[arg-type]
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to instrument FastAPI: %s", exc)
