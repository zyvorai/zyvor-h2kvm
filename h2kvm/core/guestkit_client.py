# Copyright (c) 2026 ZyvorAI Labs Private Limited.
# SPDX-License-Identifier: LicenseRef-Zyvor-Production-1.0
# https://zyvor.dev · info@zyvor.dev

"""Thin facade over hypersdk-guestkit — no duplicate disk/repair logic."""

from __future__ import annotations

import importlib
from pathlib import Path
from typing import Any

from h2kvm.core.guestfs_factory import create_guestfs


def _guestkit() -> Any:
    """Import and return the optional ``guestkit`` module (typed Any: native extension)."""
    try:
        # import_module (not an import statement): the native extension exposes no static members
        return importlib.import_module("guestkit")
    except ImportError as exc:
        raise ImportError(
            "GuestKit is required for offline disk operations.\n"
            "  pip install hypersdk-guestkit\n"
            "  or: pip install -e ~/tt/guestkit"
        ) from exc


def open_guest(path: str | Path, *, backend: str = "guestkit") -> Any:
    """Return a GuestFS-compatible handle for *path*."""
    _guestkit()
    g = create_guestfs(backend=backend)
    g.add_drive_ro(str(path))
    g.launch()
    return g


def doctor(
    path: str | Path,
    *,
    target: str = "kvm",
    explain: bool = False,
    verbose: bool = False,
) -> dict[str, Any]:
    """Run GuestKit bootability doctor."""
    return _guestkit().run_doctor(str(path), target=target, explain=explain, verbose=verbose)


def boot_inspect(
    path: str | Path,
    *,
    target: str = "kvm",
    verbose: bool = False,
) -> dict[str, Any]:
    """Summarize boot-related guest state from an offline disk."""
    return _guestkit().run_boot_inspect(str(path), target=target, verbose=verbose)


def migrate_plan(
    path: str | Path,
    *,
    target: str = "kvm",
    explain: bool = False,
    verbose: bool = False,
    export_fix_plan: bool = False,
) -> dict[str, Any]:
    """Generate a hypervisor-aware migration plan."""
    return _guestkit().run_migrate_plan(
        str(path),
        target=target,
        explain=explain,
        verbose=verbose,
        export_fix_plan=export_fix_plan,
    )


def repair_boot(
    path: str | Path,
    *,
    dry_run: bool = True,
    verbose: bool = False,
    fix_cloud_init_network: bool = False,
    validate_fstab: bool = False,
) -> dict[str, Any]:
    """Generate or apply a boot repair plan (fstab/grub/initramfs)."""
    return _guestkit().run_repair_plan(
        str(path),
        dry_run=dry_run,
        verbose=verbose,
        fix_cloud_init_network=fix_cloud_init_network,
        validate_fstab=validate_fstab,
    )


# pylint: disable-next=too-many-arguments  # keyword-only mirror of guestkit.run_migrate_repair
def migrate_repair(
    path: str | Path,
    *,
    target: str = "kvm",
    apply: bool = False,
    include_destructive: bool = False,
    virtio_win: str | Path | None = None,
    verbose: bool = False,
) -> dict[str, Any]:
    """Generate or apply a hypervisor-aware migration repair plan."""
    return _guestkit().run_migrate_repair(
        str(path),
        target=target,
        apply=apply,
        include_destructive=include_destructive,
        virtio_win=str(virtio_win) if virtio_win else None,
        verbose=verbose,
    )


def convert_disk(
    source: str | Path,
    output: str | Path,
    *,
    fmt: str = "qcow2",
    compress: bool = False,
    flatten: bool = True,
) -> dict[str, Any]:
    """Convert a disk image using GuestKit DiskConverter."""
    converter = _guestkit().DiskConverter()
    return converter.convert(str(source), str(output), fmt, compress=compress, flatten=flatten)
