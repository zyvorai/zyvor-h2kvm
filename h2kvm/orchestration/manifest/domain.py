# Copyright (c) 2026 ZyvorAI Labs Private Limited.
# SPDX-License-Identifier: LicenseRef-Zyvor-Production-1.0
# https://zyvor.dev · info@zyvor.dev

# h2kvm/orchestration/manifest/domain.py
"""Domain XML for manifest mode.

The libvirt integration stage defines a domain from ``domain.xml``; the conversion stages do not write one, so
this builds it from the manifest's VM details, the converted boot disk and the firmware the fix stage detected.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .loader import ManifestLoader


def _safe_domain_name(raw: str) -> str:
    """A libvirt-friendly domain name: letters, digits, '-', '_' and '.'."""
    return "".join(c if c.isalnum() or c in "-_." else "-" for c in raw).strip("-") or "migrated-vm"


def _domain_config(loader: ManifestLoader, *, name: str, image: Path, output_dir: Path, uefi: bool) -> Any:
    """Build the LinuxDomainConfig for a converted boot disk (libvirt helpers are imported lazily)."""
    # pylint: disable=import-outside-toplevel
    from h2kvm.libvirt.domain_emitter import auto_detect_ovmf
    from h2kvm.libvirt.libvirt_utils import default_graphics
    from h2kvm.libvirt.linux_domain import LinuxDomainConfig

    vm = loader.get_vm_metadata()
    return LinuxDomainConfig(
        name=name,
        image_path=image,
        out_dir=output_dir,
        profile="default" if uefi else "minimal-bios-gui",
        firmware="uefi" if uefi else "bios",
        memory_mib=max(512, int(vm.get("mem_gb") or 2) * 1024),
        vcpus=max(1, int(vm.get("cpu") or 2)),
        disk_type=loader.get_output_format(),
        graphics=default_graphics(),
        ovmf_code=auto_detect_ovmf() if uefi else "/usr/share/edk2/ovmf/OVMF_CODE.fd",
        write_xml=True,
        virsh_define=False,  # the libvirt stage defines it, honouring overwrite_domain
        # libvirt's qemu runs as its own user and cannot read the daemon's output directory
        copy_to_libvirt_images=True,
        overwrite_disk_copy=True,
    )


def emit_domain_xml(
    loader: ManifestLoader,
    logger: logging.Logger,
    *,
    output_dir: Path | None,
    converted_disks: dict[str, Path],
    boot_mode: str | None,
) -> Path | None:
    """Write a libvirt domain definition for the converted boot disk; returns its path, or None."""
    # pylint: disable=import-outside-toplevel
    # Deliberately lazy: the libvirt helpers are an optional dependency.
    from h2kvm.libvirt.linux_domain import emit_linux_domain

    if output_dir is None:
        return None
    if loader.get_os_hint() == "windows":
        logger.warning("⚠️  Domain XML for Windows guests is not emitted in manifest mode")
        return None

    boot_disk = loader.get_boot_disk()
    image = converted_disks.get(boot_disk.id)
    if image is None:
        logger.warning("⚠️  Boot disk %s has not been converted; no domain XML written", boot_disk.id)
        return None

    uefi = boot_mode == "uefi" or loader.get_firmware() == "uefi"
    name = _safe_domain_name(str(loader.get_source_metadata().get("vm_name") or boot_disk.id))
    logger.info("🧾 Writing domain XML: name=%s firmware=%s", name, "uefi" if uefi else "bios")
    config = _domain_config(loader, name=name, image=image, output_dir=output_dir, uefi=uefi)
    return emit_linux_domain(config).xml_path
