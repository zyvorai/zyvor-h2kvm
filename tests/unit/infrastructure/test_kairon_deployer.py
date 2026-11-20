# Copyright (c) 2026 ZyvorAI Labs Private Limited.
# SPDX-License-Identifier: LicenseRef-Zyvor-Production-1.0
# https://zyvor.dev · info@zyvor.dev

"""Unit tests for the Kairon deployer (Veyron /api/v1/imports)."""

from __future__ import annotations

import argparse
import hashlib
import urllib.request
from unittest.mock import MagicMock

import pytest

from h2kvm.cli.args.validators import validate_deploy_exclusive
from h2kvm.core.exceptions import InfrastructureError
from h2kvm.infrastructure.deployers import kairon
from h2kvm.infrastructure.deployers.kairon import (
    KaironDeployer,
    _ImageServer,
    deploy_to_kairon,
    image_format,
    vm_name_for,
)


def _args(**kw):
    base = {
        "kairon_veyron_url": "https://veyron:30151/",
        "kairon_api_key": "k",
        "kairon_namespace": "prod",
        "dry_run": False,
        "vm_name": None,
    }
    base.update(kw)
    return argparse.Namespace(**base)


def _img(tmp_path, name="web01.qcow2", data=b"qcow2-bytes"):
    p = tmp_path / name
    p.write_bytes(data)
    return p


def test_dry_run_skips_veyron(tmp_path):
    img = _img(tmp_path)
    result = deploy_to_kairon(MagicMock(), _args(dry_run=True, kairon_image_url="http://x/y"), str(img))
    assert result == {"vm_name": "web01", "namespace": "prod", "format": "qcow2", "dry_run": True}


def test_formats_and_names(tmp_path):
    assert image_format(tmp_path / "a.QCOW2") == "qcow2"
    assert image_format(tmp_path / "a.ova") == "ova"
    with pytest.raises(InfrastructureError):
        image_format(tmp_path / "a.iso")
    assert vm_name_for(argparse.Namespace(vm_name="DC1/Web_01"), tmp_path / "x.qcow2") == "dc1-web-01"
    assert vm_name_for(argparse.Namespace(), tmp_path / "db.disk0.qcow2") == "db"


def test_requires_url_or_serve(tmp_path):
    img = _img(tmp_path)
    with pytest.raises(InfrastructureError, match="kairon-image-url"):
        KaironDeployer(MagicMock(), _args()).deploy(str(img))
    with pytest.raises(InfrastructureError, match="advertise"):
        KaironDeployer(MagicMock(), _args(kairon_serve="127.0.0.1:0")).deploy(str(img))
    with pytest.raises(InfrastructureError, match="start"):
        KaironDeployer(
            MagicMock(),
            _args(kairon_serve="127.0.0.1:0", kairon_advertise_url="http://h:1", kairon_no_start=True),
        ).deploy(str(img))
    with pytest.raises(InfrastructureError, match="veyron-url"):
        KaironDeployer(MagicMock(), _args(kairon_veyron_url=None, kairon_image_url="http://x")).deploy(
            str(img)
        )


def test_payload_shape():
    d = KaironDeployer(
        MagicMock(),
        _args(kairon_cpus=4, kairon_memory="8Gi", kairon_source_hypervisor="vmware", vm_name="web01"),
    )
    body = d.payload("web01", "http://h/f.qcow2", "ab" * 32, "qcow2")
    assert body["cpus"] == 4 and body["memory"] == "8Gi"
    assert body["start"] is True and body["repair"] is False
    assert body["source"] == {"tool": "h2kvm", "hypervisor": "vmware", "vm": "web01"}
    assert body["namespace"] == "prod"


def test_image_server_serves_only_its_route(tmp_path):
    img = _img(tmp_path, data=b"x" * 1000)
    with _ImageServer(img, "127.0.0.1:0") as srv:
        base = f"http://127.0.0.1:{srv.port}"
        with urllib.request.urlopen(base + srv.route) as r:  # noqa: S310
            assert r.read() == b"x" * 1000
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(base + "/web01.qcow2")  # noqa: S310
        assert srv.completed == 1


def test_deploy_posts_import_and_waits(tmp_path, monkeypatch):
    img = _img(tmp_path)
    calls = []

    def fake_api(self, method, path, body=None):
        calls.append((method, path, body))
        return {"data": {"status": "Running" if method == "GET" else "Pending"}}

    monkeypatch.setattr(KaironDeployer, "_api", fake_api)
    result = deploy_to_kairon(MagicMock(), _args(kairon_image_url="http://files/web01.qcow2"), str(img))
    digest = hashlib.sha256(b"qcow2-bytes").hexdigest()
    assert calls[0][0:2] == ("POST", "/api/v1/imports")
    assert calls[0][2]["sha256"] == digest
    assert calls[1][0:2] == ("GET", "/api/v1/imports/prod/web01")
    assert result["status"] == "Running" and result["digest"] == f"sha256:{digest}"


def test_failed_machine_raises(tmp_path, monkeypatch):
    img = _img(tmp_path)
    monkeypatch.setattr(KaironDeployer, "_api", lambda self, m, p, b=None: {"data": {"status": "Failed"}})
    monkeypatch.setattr(kairon.time, "sleep", lambda s: None)
    with pytest.raises(InfrastructureError, match="Failed"):
        deploy_to_kairon(MagicMock(), _args(kairon_image_url="http://f/w.qcow2"), str(img))


def test_kairon_exclusive_with_other_targets():
    args = argparse.Namespace(
        deploy_k8s=True,
        deploy_openstack=False,
        deploy_kairon=True,
        emit_domain_xml=False,
        virsh_define=False,
        libvirt_test=False,
    )
    with pytest.raises(SystemExit, match="deploy_kairon is mutually exclusive"):
        validate_deploy_exclusive(args, {})
    args.deploy_k8s = False
    args.virsh_define = True
    with pytest.raises(SystemExit, match="deploy_kairon cannot be combined"):
        validate_deploy_exclusive(args, {})
