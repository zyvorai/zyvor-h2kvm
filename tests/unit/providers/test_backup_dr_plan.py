"""DR test plan: find_vm misses (None) are skipped; generic backup VM info contract."""

import logging
from datetime import datetime

import pytest

from h2kvm.providers.backup_sources.base import BackupFormat, BackupVMInfo
from h2kvm.providers.backup_sources.generic import GenericBackupSource
from h2kvm.providers.backup_sources.orchestrator import BackupRestoreOrchestrator


def _vm(name: str, size_gb: float) -> BackupVMInfo:
    return BackupVMInfo(
        backup_format=BackupFormat.GENERIC,
        vm_name=name,
        backup_date=datetime(2026, 1, 1),
        backup_type="full",
        backup_size_gb=size_gb,
        backup_location="/b",
        disks=[],
    )


def test_dr_plan_skips_missing_vms_and_orders_by_size():
    orch = BackupRestoreOrchestrator(logging.getLogger("t"))
    plan = orch.generate_dr_test_plan(
        [("s", _vm("big", 80)), None, ("s", _vm("small", 10))],
        test_env_capacity_gb=50,
    )
    assert plan["total_vms"] == 3
    assert plan["vms_in_plan"] == 1
    assert [vm.vm_name for _, vm in plan["restore_order"]] == ["small"]
    assert len(plan["warnings"]) == 1


def test_generic_get_vm_info_returns_the_single_vm(tmp_path):
    archive = tmp_path / "vm1.tar"
    archive.write_bytes(b"x")
    src = GenericBackupSource(logging.getLogger("t"), archive)
    assert src.get_vm_info("ignored").vm_name == "vm1"


def test_generic_get_vm_info_raises_when_no_vm(tmp_path):
    archive = tmp_path / "vm1.tar"
    archive.write_bytes(b"x")
    src = GenericBackupSource(logging.getLogger("t"), archive)
    src.list_vms = lambda *a, **k: []
    with pytest.raises(ValueError):
        src.get_vm_info("ignored")
