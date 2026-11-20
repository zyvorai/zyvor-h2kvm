# Copyright (c) 2026 ZyvorAI Labs Private Limited.
# SPDX-License-Identifier: LicenseRef-Zyvor-Production-1.0
# https://zyvor.dev · info@zyvor.dev

"""Manifest mode writes a domain definition for the libvirt integration stage."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from unittest.mock import patch

from h2kvm.orchestration.manifest.orchestrator import ManifestOrchestrator


def _manifest(tmp_path: Path, **vm: object) -> Path:
    disk = tmp_path / "in.qcow2"
    disk.write_bytes(b"x")
    data = {
        "manifest_version": "1.0",
        "source": {"provider": "nutanix", "vm_id": "u", "vm_name": "chimera vm/01", "export_method": "x"},
        "vm": {"cpu": 4, "mem_gb": 8, "firmware": "bios", "os_hint": "linux", **vm},
        "disks": [
            {
                "id": "disk-0",
                "source_format": "qcow2",
                "bytes": 1,
                "local_path": str(disk),
                "disk_type": "boot",
            }
        ],
        "output": {"directory": str(tmp_path / "out"), "format": "qcow2"},
    }
    path = tmp_path / "artifact-manifest.json"
    path.write_text(json.dumps(data))
    return path


def _orchestrator(tmp_path: Path, **vm: object) -> ManifestOrchestrator:
    orch = ManifestOrchestrator(_manifest(tmp_path, **vm), logging.getLogger("test"))
    orch.loader.load(orch.manifest_path)
    orch.output_dir = tmp_path / "out"
    orch.output_dir.mkdir()
    converted = orch.output_dir / "disk-0.qcow2"
    converted.write_bytes(b"x")
    orch.converted_disks["disk-0"] = converted
    return orch


class _Paths:
    def __init__(self, xml_path: Path) -> None:
        self.xml_path = xml_path


def _emit(orch: ManifestOrchestrator, has_esp: bool = False, taken: dict[str, str] | None = None):
    taken = taken or {}
    captured = {}

    def fake_emit(config):
        captured["config"] = config
        return _Paths(config.out_dir / f"{config.name}.xml")

    with (
        patch("h2kvm.libvirt.linux_domain.emit_linux_domain", fake_emit),
        patch("h2kvm.libvirt.domain_emitter.auto_detect_ovmf", return_value="/ovmf/OVMF_CODE.fd"),
        patch("h2kvm.libvirt.libvirt_utils.default_graphics", return_value="vnc"),
        patch("h2kvm.orchestration.manifest.domain._has_efi_system_partition", return_value=has_esp),
        patch("h2kvm.libvirt.linux_domain.unique_domain_name", side_effect=lambda n: taken.get(n, n)),
    ):
        result = orch._emit_domain_xml()  # private stage helper under test
    return result, captured.get("config")


def test_uefi_guest_gets_an_ovmf_domain_from_the_manifest_sizes(tmp_path):
    orch = _orchestrator(tmp_path)
    orch.boot_mode = "uefi"  # what the fix stage's guest inspection reports
    xml, config = _emit(orch)
    assert xml is not None
    assert config.firmware == "uefi" and config.profile == "default"
    assert config.ovmf_code == "/ovmf/OVMF_CODE.fd"
    assert (config.memory_mib, config.vcpus) == (8192, 4)
    assert config.image_path == orch.converted_disks["disk-0"]
    assert config.copy_to_libvirt_images is True  # libvirt's qemu cannot read the output directory
    assert config.virsh_define is False  # the libvirt stage defines it


def test_bios_guest_stays_bios(tmp_path):
    orch = _orchestrator(tmp_path)
    orch.boot_mode = "bios"
    _, config = _emit(orch)
    assert config.firmware == "bios"


def test_manifest_firmware_hint_is_honoured_without_detection(tmp_path):
    orch = _orchestrator(tmp_path, firmware="uefi")
    _, config = _emit(orch)
    assert config.firmware == "uefi"


def test_domain_name_is_made_safe(tmp_path):
    orch = _orchestrator(tmp_path)
    _, config = _emit(orch)
    assert config.name == "chimera-vm-01"


def test_windows_guests_are_not_emitted(tmp_path):
    orch = _orchestrator(tmp_path, os_hint="windows")
    xml, config = _emit(orch)
    assert xml is None and config is None


def test_nothing_is_emitted_before_the_disk_is_converted(tmp_path):
    orch = _orchestrator(tmp_path)
    orch.converted_disks.clear()
    xml, config = _emit(orch)
    assert xml is None and config is None


def test_a_one_gib_one_cpu_vm_keeps_its_size(tmp_path):
    orch = _orchestrator(tmp_path, mem_gb=1, cpu=1)
    _, config = _emit(orch)
    assert (config.memory_mib, config.vcpus) == (1024, 1)


def test_a_gpt_image_with_an_esp_boots_via_uefi_even_when_nothing_else_says_so(tmp_path):
    orch = _orchestrator(tmp_path)  # manifest hint bios, boot mode not detected
    _, config = _emit(orch, has_esp=True)
    assert config.firmware == "uefi"


def test_an_image_without_an_esp_stays_bios(tmp_path):
    orch = _orchestrator(tmp_path)
    _, config = _emit(orch, has_esp=False)
    assert config.firmware == "bios"


def test_an_existing_domain_with_the_same_name_is_not_reused(tmp_path):
    orch = _orchestrator(tmp_path)
    _, config = _emit(orch, taken={"chimera-vm-01": "chimera-vm-01-20261017-120000"})
    assert config.name == "chimera-vm-01-20261017-120000"
