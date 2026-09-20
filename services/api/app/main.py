import json
import logging
import os
import time
import uuid

from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from prometheus_client import Counter, Histogram, make_asgi_app
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from .schemas import TransferRequest
from .bancs import BancsLegacyEvent

DATABASE_URL = os.environ["DATABASE_URL"]
REDIS_URL = os.environ["REDIS_URL"]
AI_QUEUE = os.getenv("AI_QUEUE", "smartbancs:ai")

engine = create_async_engine(
    DATABASE_URL, pool_size=20, max_overflow=30,
    pool_timeout=3, pool_pre_ping=True
)
Session = async_sessionmaker(engine, expire_on_commit=False)
redis: Redis | None = None

REQUESTS = Counter("smartbancs_http_requests_total", "HTTP requests", ["method", "path", "status"])
LATENCY = Histogram("smartbancs_http_request_duration_seconds", "HTTP latency", ["path"])
TRANSFERS = Counter("smartbancs_transfers_total", "Transfers", ["status"])
DB_ERRORS = Counter("smartbancs_db_errors_total", "Database errors", ["type"])
AI_QUEUE_ERRORS = Counter(
    "smartbancs_ai_queue_errors_total",
    "Errors publishing asynchronous AI jobs",
)
SYNTHETIC_JOURNEYS = Counter(
    "smartbancs_synthetic_journeys_total",
    "Synthetic digital experience journeys",
    ["status"],
)
SYNTHETIC_LATENCY = Histogram(
    "smartbancs_synthetic_journey_duration_seconds",
    "Synthetic digital experience latency",
)
BANCS_EVENTS = Counter(
    "smartbancs_bancs_events_total",
    "Bancs adapter events",
    ["status"],
)

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("smartbancs")

tracer_provider = TracerProvider(
    resource=Resource.create({"service.name": "smartbancs-api"})
)
tracer_provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
trace.set_tracer_provider(tracer_provider)
tracer = trace.get_tracer("smartbancs.api")

@asynccontextmanager
async def lifespan(app: FastAPI):
    global redis
    redis = Redis.from_url(REDIS_URL, decode_responses=True)
    yield
    await redis.aclose()
    await engine.dispose()

app = FastAPI(title="SmartBancs API", version="1.0.0", lifespan=lifespan)
app.mount("/metrics", make_asgi_app())
FastAPIInstrumentor.instrument_app(app)

@app.get("/", include_in_schema=False)
async def dashboard():
    return FileResponse(
        "ui/index.html",
        headers={"Cache-Control": "no-store, no-cache, must-revalidate"},
    )

@app.middleware("http")
async def observability(request: Request, call_next):
    start = time.perf_counter()
    request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
    request.state.request_id = request_id
    status = 500
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    finally:
        elapsed = time.perf_counter() - start
        path = request.url.path
        LATENCY.labels(path).observe(elapsed)
        REQUESTS.labels(request.method, path, str(status)).inc()
        logger.info(json.dumps({
            "event": "http_request",
            "request_id": request_id,
            "method": request.method,
            "path": path,
            "duration_ms": round(elapsed * 1000, 2),
            "status": status
        }))

@app.get("/health")
async def health():
    async with Session() as session:
        await session.execute(text("SELECT 1"))
    return {"status": "ok"}

@app.get("/synthetic/transfer")
async def synthetic_transfer():
    """Synthetic user journey used by uptime and digital-experience monitors."""
    with tracer.start_as_current_span("synthetic.user_journey") as span:
        span.set_attribute("journey.name", "transfer-health-check")
        start = time.perf_counter()
        try:
            response = await health()
            elapsed = time.perf_counter() - start
            SYNTHETIC_JOURNEYS.labels("ok").inc()
            SYNTHETIC_LATENCY.observe(elapsed)
            response["journey_duration_ms"] = round(elapsed * 1000, 2)
            response["journey"] = "transfer-health-check"
            return response
        except Exception:
            SYNTHETIC_JOURNEYS.labels("error").inc()
            raise

@app.post("/api/v1/bancs/events", status_code=202)
async def receive_bancs_event(payload: BancsLegacyEvent, request: Request):
    """Translate one legacy Bancs event into the canonical audit format."""
    try:
        canonical = payload.to_canonical()
        async with Session.begin() as session:
            await session.execute(
                text("""
                    INSERT INTO audit_events(event_type, details)
                    VALUES ('BANCS_EVENT_NORMALIZED', CAST(:details AS jsonb))
                """),
                {
                    "details": json.dumps({
                        **canonical,
                        "request_id": request.state.request_id,
                        "source_system": "Bancs",
                    })
                },
            )
        BANCS_EVENTS.labels("accepted").inc()
        logger.info(json.dumps({
            "event": "bancs_event_normalized",
            "legacy_id": canonical["legacy_id"],
            "request_id": request.state.request_id,
        }))
        return {"status": "ACCEPTED", "legacy_id": canonical["legacy_id"]}
    except (ValueError, TypeError) as exc:
        BANCS_EVENTS.labels("rejected").inc()
        raise HTTPException(400, str(exc)) from exc

@app.post("/api/v1/transfers", status_code=201)
async def transfer(payload: TransferRequest, request: Request):
    tx_id = uuid.uuid4()
    request_id = request.state.request_id

    if payload.source_account == payload.destination_account:
        raise HTTPException(400, "Las cuentas deben ser diferentes")

    try:
        async with Session.begin() as session:
            ids = sorted([payload.source_account, payload.destination_account])
            result = await session.execute(
                text("""
                    SELECT account_id, currency, balance
                    FROM accounts
                    WHERE account_id IN (:a, :b)
                    ORDER BY account_id
                    FOR UPDATE
                """),
                {"a": ids[0], "b": ids[1]}
            )
            accounts = {r.account_id: r for r in result}

            if len(accounts) != 2:
                raise HTTPException(404, "Una o ambas cuentas no existen")

            source = accounts[payload.source_account]
            destination = accounts[payload.destination_account]

            if source.currency != payload.currency or destination.currency != payload.currency:
                raise HTTPException(400, "La moneda no coincide")

            if source.balance < payload.amount:
                TRANSFERS.labels("insufficient_funds").inc()
                raise HTTPException(409, "Fondos insuficientes")

            await session.execute(
                text("""
                    UPDATE accounts
                    SET balance = balance - :amount, version = version + 1
                    WHERE account_id = :source
                """),
                {"amount": payload.amount, "source": payload.source_account}
            )
            await session.execute(
                text("""
                    UPDATE accounts
                    SET balance = balance + :amount, version = version + 1
                    WHERE account_id = :destination
                """),
                {"amount": payload.amount, "destination": payload.destination_account}
            )
            await session.execute(
                text("""
                    INSERT INTO transactions
                    (transaction_id, source_account, destination_account, amount,
                     currency, status, completed_at)
                    VALUES (:id, :source, :destination, :amount, :currency,
                            'COMPLETED', NOW())
                """),
                {
                    "id": tx_id, "source": payload.source_account,
                    "destination": payload.destination_account,
                    "amount": payload.amount, "currency": payload.currency
                }
            )
            await session.execute(
                text("""
                    INSERT INTO audit_events(transaction_id, event_type, details)
                    VALUES (:id, 'TRANSFER_COMPLETED', CAST(:details AS jsonb))
                """),
                {
                    "id": tx_id,
                    "details": json.dumps({
                        "request_id": request_id,
                        "amount": float(payload.amount)
                    })
                }
            )

        TRANSFERS.labels("completed").inc()

        # La IA está fuera de la transacción financiera. Si la cola está
        # temporalmente caída, no se deshace una transferencia ya confirmada.
        try:
            if redis is None:
                raise RedisError("Redis no está inicializado")
            await redis.rpush(AI_QUEUE, json.dumps({
                "transaction_id": str(tx_id),
                "account_id": payload.source_account,
                "amount": float(payload.amount),
                "currency": payload.currency,
                "request_id": request_id,
                "attempt_count": 0,
                "schema_version": 1,
            }))
        except RedisError as exc:
            AI_QUEUE_ERRORS.inc()
            logger.error(json.dumps({
                "event": "ai_queue_publish_failed",
                "transaction_id": str(tx_id),
                "request_id": request_id,
                "error": str(exc)
            }))

        logger.info(json.dumps({
            "event": "transfer_completed",
            "transaction_id": str(tx_id),
            "request_id": request_id
        }))
        return {"transaction_id": str(tx_id), "status": "COMPLETED"}

    except HTTPException:
        raise
    except DBAPIError as exc:
        msg = str(exc).lower()
        if "deadlock" in msg:
            DB_ERRORS.labels("deadlock").inc()
            TRANSFERS.labels("deadlock").inc()
            logger.error(json.dumps({
                "event": "database_deadlock",
                "transaction_id": str(tx_id),
                "request_id": request_id,
                "error": str(exc)
            }))
            raise HTTPException(503, "Conflicto temporal de concurrencia; reintente")
        DB_ERRORS.labels("db_error").inc()
        logger.error(json.dumps({
            "event": "database_error",
            "transaction_id": str(tx_id),
            "request_id": request_id,
            "error": str(exc)
        }))
        raise HTTPException(503, "Base de datos temporalmente no disponible")

@app.get("/api/v1/accounts")
async def list_accounts():
    async with Session() as session:
        result = await session.execute(
            text("""
                SELECT account_id, owner_id, currency, balance, version
                FROM accounts
                ORDER BY account_id
            """)
        )
        return [dict(row) for row in result.mappings().all()]

@app.get("/api/v1/accounts/{account_id}")
async def get_account(account_id: str):
    async with Session() as session:
        result = await session.execute(
            text("""
                SELECT account_id, owner_id, currency, balance, version
                FROM accounts WHERE account_id=:id
            """),
            {"id": account_id}
        )
        row = result.mappings().first()
    if not row:
        raise HTTPException(404, "Cuenta no encontrada")
    return dict(row)

@app.get("/api/v1/transfers")
async def list_transfers(limit: int = 20):
    limit = max(1, min(limit, 100))
    async with Session() as session:
        result = await session.execute(
            text("""
                SELECT transaction_id, source_account, destination_account,
                       amount, currency, status, created_at, completed_at
                FROM transactions ORDER BY created_at DESC LIMIT :limit
            """),
            {"limit": limit}
        )
        return [dict(r) for r in result.mappings().all()]

@app.get("/api/v1/recommendations/{account_id}")
async def recommendations(account_id: str):
    async with Session() as session:
        result = await session.execute(
            text("""
                SELECT account_id, recommendation, model_version, created_at
                FROM recommendations
                WHERE account_id=:id
                ORDER BY created_at DESC LIMIT 10
            """),
            {"id": account_id}
        )
        return [dict(r) for r in result.mappings().all()]
