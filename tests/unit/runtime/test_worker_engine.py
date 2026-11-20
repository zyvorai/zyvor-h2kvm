"""Worker engine: inspect operation uses the real guest inspector; optional parameters."""

import json
from unittest.mock import MagicMock, patch

from h2kvm.core.guest_inspector import GuestInspectionResult
from h2kvm.runtime.worker.capabilities import CapabilityLevel, CapabilityDetector
from h2kvm.runtime.worker.engine import WorkerEngine
from h2kvm.runtime.worker.schemas import ArtifactConfig, AuditInfo, ImageSpec, JobSpec, OperationType
from h2kvm.runtime.worker.schemas import JobState
from h2kvm.runtime.worker.state_machine import JobStateMachine


def _spec(tmp_path, parameters=None):
    return JobSpec(
        job_id="job-1",
        operation=OperationType.INSPECT,
        image=ImageSpec(path="/images/a.qcow2", format="qcow2"),
        artifacts=ArtifactConfig(output_path=str(tmp_path)),
        audit=AuditInfo(requested_by="tester"),
        parameters=parameters,
    )


def _engine():
    return WorkerEngine(worker_id="w1", health_port=None)


def test_op_inspect_writes_report_from_guest_inspector(tmp_path):
    engine = _engine()
    spec = _spec(tmp_path)
    sm = JobStateMachine(spec.job_id, initial_state=JobState.RUNNING)

    fake = MagicMock()
    fake.inspect.return_value = GuestInspectionResult(metadata={"k": "v"})
    with patch("h2kvm.runtime.worker.engine.ComprehensiveGuestInspector", return_value=fake):
        out = engine._op_inspect(spec, sm)

    fake.inspect.assert_called_once_with("/images/a.qcow2")
    report = json.loads((tmp_path / "job-1_inspection.json").read_text())
    assert report["metadata"] == {"k": "v"}
    assert out["outputs"].report == str(tmp_path / "job-1_inspection.json")
    assert "inspection_seconds" in out["metrics"]


def test_detection_diagnostics_compares_levels_by_value():
    det = CapabilityDetector()
    with (
        patch.object(
            CapabilityDetector, "detect_capability_level", return_value=CapabilityLevel.USERSPACE_ONLY
        ),
        patch.object(CapabilityDetector, "_check_nbd_module", return_value=False),
        patch.object(CapabilityDetector, "_has_nbd_access", return_value=False),
        patch.object(CapabilityDetector, "detect_execution_mode", return_value="host"),
    ):
        report = det.get_detection_diagnostics()
    assert report["detected_level"] == "USERSPACE_ONLY"
    assert [s["step"] for s in report["skipped_steps"]] == ["nbd_inspection", "offline_fixes"]
    assert report["capabilities"]["offline_mount"] is False
    assert report["environment"]["execution_mode"] == "host"
