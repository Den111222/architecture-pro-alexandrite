from fastapi import FastAPI
import httpx
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.jaeger import JaegerPropagator
from opentelemetry.sdk.resources import Resource, SERVICE_NAME
import os

# Настройка ресурса с именем сервиса
resource = Resource(attributes={SERVICE_NAME: "service-a"})
# Настройка OTLP экспортера (Jaeger поддерживает OTLP на порту 4317)
otlp_exporter = OTLPSpanExporter(
    endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://jaeger:4317"),
    insecure=True,
)
# Консольный экспортер для отладки
console_exporter = ConsoleSpanExporter()
# Настройка OpenTelemetry
provider = TracerProvider(resource=resource)
provider.add_span_processor(BatchSpanProcessor(otlp_exporter))
provider.add_span_processor(BatchSpanProcessor(console_exporter))  # Отладка
trace.set_tracer_provider(provider)

# Настройка пропагации (W3C Trace Context)
set_global_textmap(JaegerPropagator())

# Инструментирование HTTP клиента
HTTPXClientInstrumentor().instrument()

app = FastAPI(title="Service A - Calculation Service")

# Инструментирование FastAPI
FastAPIInstrumentor.instrument_app(app)

tracer = trace.get_tracer(__name__)


@app.get("/")
async def root():
    """Главный эндпоинт, который вызывает Service B"""
    with tracer.start_as_current_span("call-service-b") as span:
        span.set_attribute("http.method", "GET")
        span.set_attribute("service.caller", "service-a")

        async with httpx.AsyncClient() as client:
            # Вызов Service B с propagation контекста
            response = await client.get("http://service-b:8080/order")
            span.set_attribute("http.status_code", response.status_code)
            span.set_attribute("service_b_response", response.text)

            return {
                "message": "Service B responded",
                "status_code": response.status_code,
                "response": response.text
            }


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8080)

