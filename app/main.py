import os
import time
from typing import Dict
from fastapi import FastAPI, HTTPException, Request, Response, status
from prometheus_client import (
    Counter,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

from app.logger import setup_logger
from app.models import (
    ProcessBatchRequest,
    ProcessBatchResponse,
    ProcessedRecord,
    HealthResponse,
)
from app.resilience import call_downstream_dependency, DownstreamServiceError

# Telemetry & Structured Logging
logger = setup_logger("service")

# Prometheus Metrics
REQUEST_COUNT = Counter(
    "http_requests_total",
    "Total HTTP Requests",
    ["method", "endpoint", "status_code"],
)
REQUEST_LATENCY = Histogram(
    "http_request_duration_seconds",
    "HTTP Request Latency in seconds",
    ["method", "endpoint"],
)
RECORDS_PROCESSED_TOTAL = Counter(
    "records_processed_total",
    "Total records parsed and processed",
    ["status"],
)

app = FastAPI(
    title="Self-Healing Containerized Service",
    description="Resilient data-processing ETL service with Kubernetes self-healing probes",
    version="1.0.0",
)

# App State for Dynamic Health & Chaos Injection
app_state: Dict[str, bool] = {
    "is_healthy": True,
    "is_ready": True,
}


@app.middleware("http")
async def prometheus_metrics_middleware(request: Request, call_next):
    start_time = time.time()
    response = None
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception as exc:
        status_code = 500
        raise exc
    finally:
        duration = time.time() - start_time
        REQUEST_COUNT.labels(
            method=request.method,
            endpoint=request.url.path,
            status_code=str(status_code if response else 500),
        ).inc()
        REQUEST_LATENCY.labels(
            method=request.method,
            endpoint=request.url.path,
        ).observe(duration)


@app.get("/health", response_model=HealthResponse, tags=["Health"])
async def health_check():
    """Health check endpoint wired to Kubernetes liveness & readiness probes."""
    if not app_state["is_healthy"]:
        logger.warning("Liveness probe check failed (simulated unhealthiness)")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy",
        )
    return HealthResponse(
        status="ok",
        service="self-healing-k8s-service",
        version="1.0.0",
        degraded=not app_state["is_ready"],
    )


@app.get("/ready", response_model=HealthResponse, tags=["Health"])
async def readiness_check():
    """Readiness probe endpoint ensuring traffic is only routed when healthy."""
    if not app_state["is_ready"] or not app_state["is_healthy"]:
        logger.warning("Readiness probe check failed (service not ready for traffic)")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service not ready",
        )
    return HealthResponse(
        status="ready",
        service="self-healing-k8s-service",
        version="1.0.0",
        degraded=False,
    )


@app.post("/process", response_model=ProcessBatchResponse, tags=["Processing"])
async def process_batch(batch: ProcessBatchRequest):
    """Processes, normalizes, and validates a batch of records."""
    logger.info("Starting batch processing", extra={"batch_id": batch.batch_id, "count": len(batch.records)})

    failure_rate = float(os.getenv("DOWNSTREAM_FAILURE_RATE", "0.0"))
    try:
        attempts = await call_downstream_dependency(
            simulated_failure_rate=failure_rate,
            max_retries=3,
        )
    except DownstreamServiceError as err:
        RECORDS_PROCESSED_TOTAL.labels(status="failed").inc(len(batch.records))
        logger.error("Processing aborted due to downstream dependency", extra={"error": str(err)})
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Downstream dependency error: {str(err)}",
        )

    processed_records = []
    for record in batch.records:
        cleaned = " ".join(record.payload.strip().split())
        words = len(cleaned.split()) if cleaned else 0
        processed_records.append(
            ProcessedRecord(
                id=record.id,
                normalized_payload=cleaned,
                priority=record.priority,
                char_count=len(cleaned),
                word_count=words,
            )
        )

    RECORDS_PROCESSED_TOTAL.labels(status="success").inc(len(batch.records))
    logger.info(
        "Batch processed successfully",
        extra={"batch_id": batch.batch_id, "processed_count": len(processed_records)},
    )

    return ProcessBatchResponse(
        batch_id=batch.batch_id,
        total_received=len(batch.records),
        total_processed=len(processed_records),
        status="COMPLETED",
        downstream_attempts=attempts,
        records=processed_records,
    )


@app.get("/metrics", tags=["Observability"])
async def metrics():
    """Prometheus metrics endpoint scraped by Prometheus server."""
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# Chaos Testing Endpoints for Demonstrating Self-Healing
@app.post("/chaos/crash", tags=["Chaos Testing"])
async def chaos_crash():
    """Simulates an internal deadlock/crash state causing liveness probe to fail."""
    app_state["is_healthy"] = False
    logger.critical("Chaos injected: Service marked as UNHEALTHY. Liveness probes will now fail.")
    return {"message": "Chaos triggered: /health will now return 503 until K8s restarts the container"}


@app.post("/chaos/degrade", tags=["Chaos Testing"])
async def chaos_degrade():
    """Simulates service degradation causing readiness probe to fail."""
    app_state["is_ready"] = False
    logger.warning("Chaos injected: Service marked as NOT READY. Readiness probe will fail.")
    return {"message": "Service degraded: traffic routing removed until recovered"}


@app.post("/chaos/recover", tags=["Chaos Testing"])
async def chaos_recover():
    """Restores healthy state."""
    app_state["is_healthy"] = True
    app_state["is_ready"] = True
    logger.info("Service manually recovered to healthy state")
    return {"message": "Service recovered successfully"}
