# Copyright (c) 2026 ZyvorAI Labs Private Limited.
# SPDX-License-Identifier: LicenseRef-Zyvor-Production-1.0
# https://zyvor.dev · info@zyvor.dev

"""Tests for the DHCP fallback installed on guests with no network configuration."""

from __future__ import annotations

import logging

from h2kvm.fixers.network.core import NetworkFixer
from h2kvm.fixers.network.dhcp_fallback import (
    NETPLAN_PATH,
    NETWORKD_PATH,
    detect_backend,
    install_dhcp_fallback,
)
from h2kvm.fixers.network.model import FixLevel

LOG = logging.getLogger("test")


class FakeGuest:
    """Minimal in-memory stand-in for the guestfs handle."""

    def __init__(
        self, files: set[str] | None = None, dirs: set[str] | None = None, fail_write: bool = False
    ):
        self.files = set(files or ())
        self.dirs = set(dirs or ())
        self.written: dict[str, bytes] = {}
        self.modes: dict[str, int] = {}
        self.fail_write = fail_write

    def exists(self, path: str) -> bool:
        return path in self.files or path in self.dirs or path in self.written

    def is_dir(self, path: str) -> bool:
        return path in self.dirs

    def mkdir_p(self, path: str) -> None:
        self.dirs.add(path)

    def write(self, path: str, data: bytes) -> None:
        if self.fail_write:
            raise OSError("read-only")
        self.written[path] = data

    def chmod(self, mode: int, path: str) -> None:
        self.modes[path] = mode

    # NetworkDiscovery probes these when listing configs; none exist on a bare cloud image.
    def glob_expand(self, _pattern: str) -> list[str]:
        return []

    def is_file(self, _path: str) -> bool:
        return False


def test_netplan_guest_gets_dhcp_config():
    g = FakeGuest(dirs={"/etc/netplan"})
    res = install_dhcp_fallback(g, LOG)
    assert res == {
        "installed": True,
        "backend": "netplan",
        "path": NETPLAN_PATH,
        "reason": "no network configuration found",
    }
    assert b"dhcp4: true" in g.written[NETPLAN_PATH]
    assert g.modes[NETPLAN_PATH] == 0o600  # netplan warns on group/world-readable files


def test_netplan_detected_from_binary_when_dir_missing():
    g = FakeGuest(files={"/usr/sbin/netplan"})
    assert detect_backend(g) == "netplan"
    assert install_dhcp_fallback(g, LOG)["path"] == NETPLAN_PATH
    assert "/etc/netplan" in g.dirs


def test_networkd_guest_gets_dhcp_network_file():
    g = FakeGuest(files={"/usr/lib/systemd/system/systemd-networkd.service"})
    res = install_dhcp_fallback(g, LOG)
    assert res["backend"] == "networkd" and res["path"] == NETWORKD_PATH
    assert b"DHCP=ipv4" in g.written[NETWORKD_PATH]


def test_unknown_stack_is_left_alone():
    g = FakeGuest()
    res = install_dhcp_fallback(g, LOG)
    assert res["installed"] is False and res["backend"] is None
    assert not g.written


def test_dry_run_writes_nothing():
    g = FakeGuest(dirs={"/etc/netplan"})
    res = install_dhcp_fallback(g, LOG, dry_run=True)
    assert res["installed"] is False and res["path"] == NETPLAN_PATH
    assert not g.written


def test_write_failure_does_not_raise():
    g = FakeGuest(dirs={"/etc/netplan"}, fail_write=True)
    res = install_dhcp_fallback(g, LOG)
    assert res["installed"] is False and "write failed" in res["reason"]


def test_fixer_installs_fallback_when_no_configs_found():
    g = FakeGuest(dirs={"/etc/netplan"})
    result = NetworkFixer(LOG, FixLevel.MODERATE).fix_network_config(g)
    assert result["dhcp_fallback"]["installed"] is True
    assert NETPLAN_PATH in g.written
    assert "installed a DHCP fallback" in result["recommendations"][0]


def test_ensure_installs_when_no_configs(monkeypatch):
    from h2kvm.fixers.network import dhcp_fallback
    from h2kvm.fixers.network.discovery import NetworkDiscovery

    monkeypatch.setattr(NetworkDiscovery, "find_network_configs", lambda self, g: [])
    g = FakeGuest(dirs={"/etc/netplan"})
    res = dhcp_fallback.ensure_dhcp_fallback(g, LOG)
    assert res["installed"] is True and NETPLAN_PATH in g.written


def test_ensure_leaves_configured_guest_alone(monkeypatch):
    from h2kvm.fixers.network import dhcp_fallback
    from h2kvm.fixers.network.discovery import NetworkDiscovery

    monkeypatch.setattr(NetworkDiscovery, "find_network_configs", lambda self, g: [object()])
    g = FakeGuest(dirs={"/etc/netplan"})
    res = dhcp_fallback.ensure_dhcp_fallback(g, LOG)
    assert res["installed"] is False and "already has 1 network configuration" in res["reason"]
    assert not g.written


def test_ensure_skips_windows_like_guest(monkeypatch):
    from h2kvm.fixers.network import dhcp_fallback
    from h2kvm.fixers.network.discovery import NetworkDiscovery

    monkeypatch.setattr(NetworkDiscovery, "find_network_configs", lambda self, g: [])
    g = FakeGuest(files={"/Windows/System32/config/SYSTEM"})
    res = dhcp_fallback.ensure_dhcp_fallback(g, LOG)
    assert res["installed"] is False and res["backend"] is None and not g.written
