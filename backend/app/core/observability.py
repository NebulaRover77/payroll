from typing import Optional

from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from .config import settings

RESOURCE = Resource.create({"service.name": "payroll-api", "deployment.env": settings.env})


def configure_tracing(otlp_endpoint: Optional[str] = None) -> None:
    tracer_provider = TracerProvider(resource=RESOURCE)
    endpoint = otlp_endpoint or settings.otlp_endpoint
    if endpoint:
        tracer_provider.add_span_processor(
            BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint))
        )
    trace.set_tracer_provider(tracer_provider)


def configure_metrics(otlp_endpoint: Optional[str] = None) -> None:
    endpoint = otlp_endpoint or settings.otlp_endpoint
    metric_reader = None
    if endpoint:
        metric_reader = PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=endpoint))
    provider_kwargs = {"resource": RESOURCE}
    if metric_reader:
        provider_kwargs["metric_readers"] = [metric_reader]
    meter_provider = MeterProvider(**provider_kwargs)
    metrics.set_meter_provider(meter_provider)


def configure_observability() -> None:
    configure_tracing()
    configure_metrics()
