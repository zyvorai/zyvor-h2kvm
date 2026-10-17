"""Worker REST API: registries are wired to methods that really exist."""

from datetime import datetime, timedelta

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

from h2kvm.runtime.worker import api
from h2kvm.runtime.worker.events import EventStore
from h2kvm.runtime.worker.scheduler import JobQueue, WorkerRegistry
from h2kvm.runtime.worker.schemas import (
    ArtifactConfig,
    AuditInfo,
    ImageSpec,
    JobSpec,
    JobState,
    OperationType,
    WorkerCapabilities,
)
from h2kvm.runtime.worker.state_machine import JobRegistry


def _spec(job_id: str, priority: int = 5) -> JobSpec:
    spec = JobSpec(
        job_id=job_id,
        operation=OperationType.INSPECT,
        image=ImageSpec(path="/images/a.qcow2", format="qcow2"),
        artifacts=ArtifactConfig(output_path="/tmp/out"),
        audit=AuditInfo(requested_by="tester"),
    )
    spec.execution_policy.priority = priority
    return spec


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "_api_token", None)
    monkeypatch.setattr(api, "job_registry", JobRegistry(tmp_path / "jobs"))
    monkeypatch.setattr(api, "job_queue", JobQueue(tmp_path / "queue"))
    monkeypatch.setattr(api, "worker_registry", WorkerRegistry(heartbeat_timeout=300))
    monkeypatch.setattr(api, "event_store", EventStore(tmp_path / "events"))
    return TestClient(api.app)


def _worker(worker_id: str, heartbeat_age_s: int = 0) -> WorkerCapabilities:
    return WorkerCapabilities(
        worker_id=worker_id,
        capabilities={"nbd": True},
        memory_gb=8,
        disk_space_gb=100,
        os_info={"name": "rhel"},
        last_heartbeat=datetime.utcnow() - timedelta(seconds=heartbeat_age_s),
    )


def test_registry_load_all_and_queue_roundtrip(tmp_path):
    reg = JobRegistry(tmp_path / "jobs")
    reg.register(_spec("job-a"))
    fresh = JobRegistry(tmp_path / "jobs")
    assert fresh.load_all() == 1
    assert "job-a" in fresh.jobs

    queue = JobQueue(tmp_path / "queue")
    queue.enqueue(_spec("job-q", priority=2))
    queue.save()
    queue.load()
    assert queue.size() == 1
    stats = queue.get_stats()
    assert stats["total_jobs"] == 1
    assert stats["by_priority"][2] == 1


def test_cleanup_stale_removes_only_expired_workers():
    reg = WorkerRegistry(heartbeat_timeout=300)
    reg.register(_worker("fresh"))
    reg.register(_worker("old", heartbeat_age_s=1000))
    assert reg.cleanup_stale() == ["old"]
    assert [w.worker_id for w in reg.list_workers(only_alive=False)] == ["fresh"]


def test_list_jobs_filters_by_state_and_skips_missing(client):
    api.job_registry.register(_spec("job-1"))
    sm2 = api.job_registry.register(_spec("job-2"))
    sm2.transition(JobState.VALIDATED, "ok")
    sm2.save(api.job_registry.state_dir)

    everything = client.get("/jobs").json()
    assert everything["total"] == 2

    validated = client.get("/jobs", params={"state": JobState.VALIDATED.value}).json()
    assert [j["job_id"] for j in validated["jobs"]] == ["job-2"]


def test_get_job_status_builds_placeholder_spec(client):
    api.job_registry.register(_spec("inspect-123"))
    body = client.get("/jobs/inspect-123").json()
    assert body["job_id"] == "inspect-123"
    assert body["spec"]["operation"] == "inspect"
    assert client.get("/jobs/nope").status_code == 404


def test_workers_listing_uses_registered_capabilities(client):
    api.worker_registry.register(_worker("w1"))
    api.worker_registry.register(_worker("w2", heartbeat_age_s=1000))
    body = client.get("/workers").json()
    assert body["total"] == 2
    assert body["active"] == 1
    assert body["workers"] == [
        {"worker_id": "w1", "capabilities": {"nbd": True}, "system_info": {"name": "rhel"}}
    ]


def test_queue_status_and_health(client):
    api.job_queue.enqueue(_spec("job-q", priority=3))
    api.job_registry.register(_spec("job-1"))
    q = client.get("/queue").json()
    assert q["total_jobs"] == 1
    assert q["by_priority"]["3"] == 1
    health = client.get("/health").json()
    assert health["status"] == "healthy"
    assert health["active_jobs"] == 1


def test_metrics_endpoint_returns_prometheus_text(client):
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")


def test_lifespan_startup_and_shutdown_use_real_registry_methods(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "_api_token", None)
    monkeypatch.setattr(api, "job_registry", JobRegistry(tmp_path / "jobs"))
    monkeypatch.setattr(api, "job_queue", JobQueue(tmp_path / "queue"))
    monkeypatch.setattr(api, "worker_registry", WorkerRegistry())
    with TestClient(api.app) as c:
        assert c.get("/healthz").status_code == 200
