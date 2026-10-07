import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app, app_state
from app.resilience import call_downstream_dependency, DownstreamServiceError


@pytest.fixture(autouse=True)
def reset_app_state():
    app_state["is_healthy"] = True
    app_state["is_ready"] = True
    yield
    app_state["is_healthy"] = True
    app_state["is_ready"] = True


@pytest.mark.asyncio
async def test_health_check_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["service"] == "self-healing-k8s-service"
        assert data["degraded"] is False


@pytest.mark.asyncio
async def test_readiness_check_ok():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/ready")
        assert response.status_code == 200
        assert response.json()["status"] == "ready"


@pytest.mark.asyncio
async def test_process_batch_success():
    transport = ASGITransport(app=app)
    payload = {
        "batch_id": "batch-101",
        "records": [
            {"id": "rec-1", "payload": "  hello    world  from  stream ", "priority": 1},
            {"id": "rec-2", "payload": "kubernetes self-healing demo", "priority": 3},
        ],
    }
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/process", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["batch_id"] == "batch-101"
        assert data["total_received"] == 2
        assert data["total_processed"] == 2
        assert data["status"] == "COMPLETED"
        assert data["records"][0]["normalized_payload"] == "hello world from stream"
        assert data["records"][0]["word_count"] == 4


@pytest.mark.asyncio
async def test_metrics_endpoint():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/metrics")
        assert response.status_code == 200
        assert "http_requests_total" in response.text
        assert "http_request_duration_seconds" in response.text


@pytest.mark.asyncio
async def test_chaos_crash_fails_liveness():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        chaos_resp = await client.post("/chaos/crash")
        assert chaos_resp.status_code == 200

        health_resp = await client.get("/health")
        assert health_resp.status_code == 503

        # Recover
        await client.post("/chaos/recover")
        recover_resp = await client.get("/health")
        assert recover_resp.status_code == 200


@pytest.mark.asyncio
async def test_chaos_degrade_fails_readiness():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        await client.post("/chaos/degrade")
        ready_resp = await client.get("/ready")
        assert ready_resp.status_code == 503

        # Liveness remains healthy when only degraded
        health_resp = await client.get("/health")
        assert health_resp.status_code == 200
        assert health_resp.json()["degraded"] is True


@pytest.mark.asyncio
async def test_retry_backoff_exhaustion():
    with pytest.raises(DownstreamServiceError):
        # 100% failure rate must exhaust retries
        await call_downstream_dependency(
            simulated_failure_rate=1.0,
            max_retries=3,
            base_delay=0.01,
        )


@pytest.mark.asyncio
async def test_retry_backoff_success():
    # 0% failure rate succeeds on first attempt
    attempts = await call_downstream_dependency(
        simulated_failure_rate=0.0,
        max_retries=3,
    )
    assert attempts == 1
