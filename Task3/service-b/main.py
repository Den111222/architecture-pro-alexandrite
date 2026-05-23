from fastapi import FastAPI, Request
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.jaeger import JaegerPropagator
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
import asyncio
import os

# Настройка ресурса с именем сервиса
resource = Resource(attributes={SERVICE_NAME: "service-b"})

# Настройка OTLP экспортера
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317"),
    insecure=True,
)

# Настройка OpenTelemetry
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
trace.set_tracer_provider(provider)

set_global_textmap(JaegerPropagator())

app = FastAPI(title="Service B - Order Service")

# Инструментирование FastAPI
FastAPIInstrumentor.instrument_app(app)

tracer = trace.get_tracer(__name__)


@app.get("/order")
async def get_order(request: Request):
    """Возвращает статус заказа (демо)"""
    with tracer.start_as_current_span("service-b.get_order") as span:
        # Добавляем атрибуты в спан
        span.set_attribute("order.status", "PROCESSING")
        span.set_attribute("order.id", "DEMO-12345")
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.route", "/order")

        # Имитация небольшой задержки
        await asyncio.sleep(0.05)

        return {
            "order_id": "DEMO-12345",
            "status": "PROCESSING",
            "message": "Заказ в обработке"
        }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)
