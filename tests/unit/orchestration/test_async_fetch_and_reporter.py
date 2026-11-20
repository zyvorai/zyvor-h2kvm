"""Regression tests: async Fetch must be awaited; reporter must report the real version."""

import argparse
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from h2kvm import __version__
from h2kvm.orchestration.disk_discovery import DiskDiscovery
from h2kvm.orchestration.manifest.reporter import ManifestReporter


def test_fetch_and_fix_awaits_async_fetch(tmp_path):
    seen = {}

    async def fake_fetch(logger, sshc, remote, outdir, fetch_all, **kw):
        seen["args"] = (remote, Path(outdir), fetch_all)
        return Path(outdir) / "disk.vmdk"

    args = argparse.Namespace(
        cmd="fetch-and-fix",
        host="esxi",
        user="root",
        port=22,
        remote="/vmfs/volumes/ds/vm/vm.vmdk",
        fetch_dir=str(tmp_path / "dl"),
        fetch_all=True,
        ssh_opt=None,
    )
    dd = DiskDiscovery(logging.getLogger("t"), args)
    with (
        patch("h2kvm.orchestration.disk_discovery.SSHClient", MagicMock()),
        patch("h2kvm.orchestration.disk_discovery.Fetch.fetch_descriptor_and_extent", fake_fetch),
    ):
        disks, tmp = dd.discover(tmp_path)

    assert disks == [tmp_path / "dl" / "disk.vmdk"]
    assert tmp is None
    assert seen["args"] == ("/vmfs/volumes/ds/vm/vm.vmdk", tmp_path / "dl", True)


def test_reporter_reports_package_version():
    assert ManifestReporter.__dict__["_get_h2kvm_version"](object()) == __version__
