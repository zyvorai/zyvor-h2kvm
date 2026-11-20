# Copyright (c) 2026 ZyvorAI Labs Private Limited.
# SPDX-License-Identifier: LicenseRef-Zyvor-Production-1.0
# https://zyvor.dev · info@zyvor.dev

# h2kvm/fixers/network/dhcp_fallback.py
"""
DHCP fallback for guests that arrive with no network configuration at all.

Cloud images (for example Ubuntu's ``*-cloudimg-*.img``, as exported from Nutanix
or any other platform) ship no netplan/networkd files and rely on cloud-init to
generate them from a datasource. After a hypervisor exit there is no datasource,
so cloud-init does not run its stages at all (observed on Ubuntu 24.04: the boot
console shows no cloud-init units, ``systemd-networkd`` starts with nothing to
configure and ``systemd-networkd-wait-online`` fails) and the NIC stays
unconfigured. This module installs a minimal "DHCP on any ethernet device"
configuration so the migrated VM is reachable on first boot, without touching
guests that already have a config.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import logging

NETPLAN_PATH = "/etc/netplan/60-h2kvm-dhcp.yaml"
NETWORKD_PATH = "/etc/systemd/network/20-h2kvm-dhcp.network"

NETPLAN_CONTENT = """\
# Written by h2kvm: this guest had no network configuration after migration.
# Remove this file if cloud-init or your own configuration takes over.
network:
  version: 2
  ethernets:
    h2kvm-dhcp:
      match:
        name: "e*"
      dhcp4: true
      optional: true
"""

NETWORKD_CONTENT = """\
# Written by h2kvm: this guest had no network configuration after migration.
# Remove this file if your own configuration takes over.
[Match]
Name=e*

[Network]
DHCP=ipv4
"""

_NETPLAN_BINARIES = ("/usr/sbin/netplan", "/usr/bin/netplan", "/sbin/netplan")
_NETWORKD_UNITS = (
    "/usr/lib/systemd/system/systemd-networkd.service",
    "/lib/systemd/system/systemd-networkd.service",
)


def _exists(g: Any, path: str) -> bool:
    try:
        return bool(g.exists(path))
    except Exception:  # pylint: disable=broad-exception-caught  # probe only; absent means "no"
        return False


def _is_dir(g: Any, path: str) -> bool:
    try:
        return bool(g.is_dir(path))
    except Exception:  # pylint: disable=broad-exception-caught  # probe only; absent means "no"
        return False


def detect_backend(g: Any) -> str | None:
    """Return ``"netplan"``, ``"networkd"`` or ``None`` for the renderer the guest can use."""
    if _is_dir(g, "/etc/netplan") or any(_exists(g, p) for p in _NETPLAN_BINARIES):
        return "netplan"
    if any(_exists(g, p) for p in _NETWORKD_UNITS):
        return "networkd"
    return None


def install_dhcp_fallback(g: Any, logger: logging.Logger, *, dry_run: bool = False) -> dict[str, Any]:
    """
    Install a DHCP-on-ethernet configuration for a guest that has none.

    Call only after discovery found no network configuration. Guests managed by
    NetworkManager or ifupdown are left alone (they either already have a
    config or run DHCP by default).

    Returns:
        ``{"installed": bool, "backend": str | None, "path": str | None, "reason": str}``
    """
    backend = detect_backend(g)
    if backend is None:
        reason = "no netplan or systemd-networkd in the guest; left unchanged"
        logger.info("DHCP fallback skipped: %s", reason)
        return {"installed": False, "backend": None, "path": None, "reason": reason}

    path, content, mode = (
        (NETPLAN_PATH, NETPLAN_CONTENT, 0o600)
        if backend == "netplan"
        else (NETWORKD_PATH, NETWORKD_CONTENT, 0o644)
    )
    if dry_run:
        logger.info("DHCP fallback (dry run): would write %s", path)
        return {"installed": False, "backend": backend, "path": path, "reason": "dry run"}

    try:
        g.mkdir_p(path.rsplit("/", 1)[0])
        g.write(path, content.encode("utf-8"))
        g.chmod(mode, path)
    except Exception as e:  # pylint: disable=broad-exception-caught  # a failed fallback must not abort the migration
        logger.warning("DHCP fallback could not be installed at %s: %s", path, e)
        return {"installed": False, "backend": backend, "path": path, "reason": f"write failed: {e}"}

    logger.info("Installed DHCP fallback for a guest with no network configuration: %s (%s)", path, backend)
    return {"installed": True, "backend": backend, "path": path, "reason": "no network configuration found"}


def ensure_dhcp_fallback(g: Any, logger: logging.Logger, *, dry_run: bool = False) -> dict[str, Any]:
    """
    Install the DHCP fallback only when the guest has no network configuration.

    This is the entry point for the GuestKit pipeline, which does not run the
    legacy network fixer: it looks for existing configuration first and leaves
    configured guests (and Windows guests, which have neither netplan nor
    systemd-networkd) alone.
    """
    # Imported here to keep this module importable without the discovery helpers' dependencies.
    from .discovery import NetworkDiscovery  # pylint: disable=import-outside-toplevel

    configs = NetworkDiscovery(logger=logger, backup_suffix=".h2kvm_backup").find_network_configs(g)
    if configs:
        return {
            "installed": False,
            "backend": None,
            "path": None,
            "reason": f"guest already has {len(configs)} network configuration file(s)",
        }
    return install_dhcp_fallback(g, logger, dry_run=dry_run)
