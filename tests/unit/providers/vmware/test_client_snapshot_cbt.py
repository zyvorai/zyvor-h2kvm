"""VMwareClient snapshot / CBT / inventory helpers used by VsphereCommands."""

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from h2kvm.core.exceptions import VMwareError
from h2kvm.providers.vmware.clients.client import VMwareClient

_MOD = "h2kvm.providers.vmware.clients.client"


@pytest.fixture
def client():
    c = VMwareClient.__new__(VMwareClient)
    c.logger = MagicMock()
    c.wait_for_task = MagicMock()
    return c


def test_create_snapshot_waits_for_task_and_returns_result(client):
    vm = MagicMock()
    task = MagicMock()
    task.info.result = SimpleNamespace(_moId="snapshot-42")
    vm.CreateSnapshot_Task.return_value = task

    snap = client.create_snapshot(vm, "pre-migration", quiesce=False, memory=True, description="d")

    vm.CreateSnapshot_Task.assert_called_once_with(
        name="pre-migration", description="d", memory=True, quiesce=False
    )
    client.wait_for_task.assert_called_once_with(task)
    assert VMwareClient.snapshot_moref(snap) == "snapshot-42"


def test_snapshot_moref_falls_back_to_str():
    assert VMwareClient.snapshot_moref("snapshot-7") == "snapshot-7"


def test_enable_cbt_reconfigures_vm(client):
    vm = MagicMock()
    fake_vim = MagicMock()
    with patch(f"{_MOD}.PYVMOMI_AVAILABLE", True), patch(f"{_MOD}.vim", fake_vim):
        client.enable_cbt(vm)
    spec = fake_vim.vm.ConfigSpec.return_value
    assert spec.changeTrackingEnabled is True
    vm.ReconfigVM_Task.assert_called_once_with(spec)
    client.wait_for_task.assert_called_once()


def test_query_changed_disk_areas_passes_arguments(client):
    vm = MagicMock()
    out = client.query_changed_disk_areas(vm, snapshot="s", device_key=2000, start_offset=5, change_id="abc")
    vm.QueryChangedDiskAreas.assert_called_once_with(
        snapshot="s", deviceKey=2000, startOffset=5, changeId="abc"
    )
    assert out is vm.QueryChangedDiskAreas.return_value


def test_disk_backing_filename():
    disk = SimpleNamespace(backing=SimpleNamespace(fileName="[ds1] vm/vm.vmdk"))
    assert VMwareClient._vm_disk_backing_filename(disk) == "[ds1] vm/vm.vmdk"
    with pytest.raises(VMwareError):
        VMwareClient._vm_disk_backing_filename(SimpleNamespace(backing=None))


def test_list_vm_names_sorted_and_view_destroyed(client):
    content = MagicMock()
    view = content.viewManager.CreateContainerView.return_value
    view.view = [SimpleNamespace(name="b"), SimpleNamespace(name="a")]
    client._content = MagicMock(return_value=content)
    with patch(f"{_MOD}.PYVMOMI_AVAILABLE", True), patch(f"{_MOD}.vim", MagicMock()):
        assert client.list_vm_names() == ["a", "b"]
    view.Destroy.assert_called_once()
