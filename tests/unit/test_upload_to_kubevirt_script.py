"""Regression tests for upload-to-kubevirt.sh (stubbed kubectl/virtctl)."""

import os
import stat
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path(__file__).resolve().parents[2] / "upload-to-kubevirt.sh"


def _stub(path: Path, body: str) -> None:
    path.write_text("#!/bin/bash\n" + body)
    path.chmod(path.stat().st_mode | stat.S_IXUSR)


@pytest.fixture
def env(tmp_path):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    log = tmp_path / "virtctl.log"
    _stub(bin_dir / "virtctl", f'echo "$@" >> {log}\n')
    e = dict(os.environ, PATH=f"{bin_dir}:{os.environ['PATH']}")
    e.pop("UPLOADPROXY_URL", None)
    return e, bin_dir, log, tmp_path


def _run(e, image):
    e = dict(e, QCOW2_IMAGE=str(image))
    return subprocess.run(["bash", str(SCRIPT), "ns"], env=e, capture_output=True, text=True)


def test_missing_image_fails(env):
    e, bin_dir, log, tmp = env
    _stub(bin_dir / "kubectl", "exit 0\n")
    r = _run(e, tmp / "nope.qcow2")
    assert r.returncode != 0
    assert "Image not found" in r.stderr
    assert not log.exists()


def test_failed_proxy_lookup_does_not_upload(env):
    e, bin_dir, log, tmp = env
    img = tmp / "a.qcow2"
    img.write_text("x")
    _stub(bin_dir / "kubectl", 'if [ "$1" = get ]; then exit 1; fi\nexit 0\n')
    r = _run(e, img)
    assert r.returncode != 0
    assert "cdi-uploadproxy" in r.stderr
    assert not log.exists()


def test_empty_proxy_ip_does_not_upload(env):
    e, bin_dir, log, tmp = env
    img = tmp / "a.qcow2"
    img.write_text("x")
    _stub(bin_dir / "kubectl", "exit 0\n")
    r = _run(e, img)
    assert r.returncode != 0
    assert not log.exists()


def test_success_uses_proxy_ip(env):
    e, bin_dir, log, tmp = env
    img = tmp / "a.qcow2"
    img.write_text("x")
    _stub(bin_dir / "kubectl", 'if [ "$1" = get ]; then echo 10.0.0.9; fi\nexit 0\n')
    r = _run(e, img)
    assert r.returncode == 0, r.stderr
    assert "--uploadproxy-url=https://10.0.0.9:443" in log.read_text()
