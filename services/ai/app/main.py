import asyncio
import json
import logging
import os

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import Counter, Gauge, make_asgi_app
from redis.asyncio import Redis
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

REDIS_URL = os.environ["REDIS_URL"]
AI_QUEUE = os.getenv("AI_QUEUE", "smartbancs:ai")
DATABASE_URL = os.environ["DATABASE_URL"]
MODEL_VERSION = "demo-1.0"
MAX_ATTEMPTS = 3
DLQ = f"{AI_QUEUE}:dlq"

redis = Redis.from_url(REDIS_URL, decode_responses=True)
engine = create_async_engine(DATABASE_URL, pool_size=5, max_overflow=5)
Session = async_sessionmaker(engine, expire_on_commit=False)

AI_JOBS = Counter("smartbancs_ai_jobs_total", "AI jobs", ["status"])
AI_RETRIES = Counter("smartbancs_ai_retries_total", "AI job retries")
AI_DLQ = Counter("smartbancs_ai_dlq_total", "AI jobs moved to dead letter queue")
AI_QUEUE_DEPTH = Gauge("smartbancs_ai_queue_depth", "Pending AI jobs")
AI_COMPLETED = 0
logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("smartbancs-ai")
provider = TracerProvider(
    resource=Resource.create({"service.name": "smartbancs-ai"})
)
provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("smartbancs.ai")

def recommendation_for(amount: float) -> str:
    if amount >= 500:
        return "Revisar presupuesto mensual y mantener un fondo de emergencia."
    if amount >= 100:
        return "Comparar gastos recurrentes y establecer una meta de ahorro."
    return "Mantener seguimiento de gastos pequeños para detectar patrones."

async def worker():
    global AI_COMPLETED
    while True:
        data = None
        try:
            item = await redis.blpop(AI_QUEUE, timeout=5)
            if not item:
                continue
            _, payload = item
            data = json.loads(payload)
            attempt_count = int(data.get("attempt_count", 0))
            AI_QUEUE_DEPTH.set(await redis.llen(AI_QUEUE))

            with tracer.start_as_current_span("ai.recommendation") as span:
                span.set_attribute("transaction.id", data["transaction_id"])
                span.set_attribute("request.id", data.get("request_id", "unknown"))
                span.set_attribute("ai.attempt", attempt_count)
                # Simulación de inferencia lenta; el API transaccional no espera aquí.
                await asyncio.sleep(0.5)
                recommendation = recommendation_for(data["amount"])

                async with Session.begin() as session:
                    await session.execute(
                        text("""
                            INSERT INTO recommendations
                            (account_id, source_transaction_id, recommendation, model_version)
                            VALUES (:account_id, :transaction_id, :recommendation, :model_version)
                            ON CONFLICT (source_transaction_id)
                            WHERE source_transaction_id IS NOT NULL DO NOTHING
                        """),
                        {
                            "account_id": data["account_id"],
                            "transaction_id": data["transaction_id"],
                            "recommendation": recommendation,
                            "model_version": MODEL_VERSION
                        }
                    )

            AI_JOBS.labels("completed").inc()
            AI_COMPLETED += 1
            logger.info(json.dumps({
                "event": "ai_job_completed",
                "transaction_id": data["transaction_id"],
                "request_id": data.get("request_id"),
                "model_version": MODEL_VERSION
            }))
        except Exception as exc:
            AI_JOBS.labels("error").inc()
            if data is not None and attempt_count < MAX_ATTEMPTS:
                data["attempt_count"] = attempt_count + 1
                await asyncio.sleep(2 ** attempt_count)
                await redis.rpush(AI_QUEUE, json.dumps(data))
                AI_RETRIES.inc()
                logger.error(json.dumps({
                    "event": "ai_job_retry",
                    "transaction_id": data.get("transaction_id"),
                    "request_id": data.get("request_id"),
                    "attempt_count": data["attempt_count"],
                    "error": str(exc)
                }))
            elif data is not None:
                await redis.rpush(DLQ, payload)
                AI_DLQ.inc()
                logger.error(json.dumps({
                    "event": "ai_job_dead_lettered",
                    "transaction_id": data.get("transaction_id"),
                    "request_id": data.get("request_id"),
                    "error": str(exc)
                }))
            else:
                logger.error(json.dumps({"event": "ai_job_error", "error": str(exc)}))
            await asyncio.sleep(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as connection:
        await connection.execute(text(
            "ALTER TABLE recommendations ADD COLUMN IF NOT EXISTS "
            "source_transaction_id UUID"
        ))
        await connection.execute(text(
            "CREATE UNIQUE INDEX IF NOT EXISTS "
            "ux_recommendations_source_transaction "
            "ON recommendations(source_transaction_id) "
            "WHERE source_transaction_id IS NOT NULL"
        ))
    task = asyncio.create_task(worker())
    yield
    task.cancel()
    await redis.aclose()
    await engine.dispose()

app = FastAPI(title="SmartBancs AI Service", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8000"],
    allow_methods=["GET"],
    allow_headers=["*"],
)
app.mount("/metrics", make_asgi_app())
FastAPIInstrumentor.instrument_app(app)

@app.get("/health")
async def health():
    return {"status": "ok", "model_version": MODEL_VERSION}

@app.get("/summary")
async def summary():
    async with Session() as session:
        result = await session.execute(text(
            "SELECT COUNT(*) FROM recommendations "
            "WHERE source_transaction_id IS NOT NULL"
        ))
        persisted_completed = int(result.scalar_one())
    return {
        "jobs_completed": persisted_completed,
        "jobs_completed_since_start": AI_COMPLETED,
        "jobs_failed": int(AI_JOBS.labels("error")._value.get()),
        "queue_depth": int(AI_QUEUE_DEPTH._value.get()),
        "model_version": MODEL_VERSION,
    }
