# Copyright (c) 2026 ZyvorAI Labs Private Limited.
# SPDX-License-Identifier: LicenseRef-Zyvor-Production-1.0
# https://zyvor.dev · info@zyvor.dev

"""
Kairon deployment: land the converted disk as a Kairon ``Machine`` through Veyron.

Kairon boots a Machine from an ``http(s)://`` image URL pinned by sha256: kairon-node
downloads the file into its digest-keyed cache, converts OVA/VMDK/VHD(X) if needed and
boots a per-Machine overlay. No KubeVirt, CDI or PVC upload is involved.

The disk must be reachable from the Kairon node. Either pass ``--kairon-image-url`` for a
file you already published, or ``--kairon-serve`` to have h2kvm serve it over HTTP until
the VM is running.
"""

from __future__ import annotations

import hashlib
import http.server
import json
import os
import secrets
import shutil
import ssl
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from h2kvm.core.exceptions import InfrastructureError

FORMATS = {
    ".qcow2": "qcow2",
    ".raw": "raw",
    ".img": "raw",
    ".ova": "ova",
    ".vmdk": "vmdk",
    ".vhd": "vhd",
    ".vhdx": "vhdx",
}
SETTLED = {"Running"}
FAILED = {"Failed", "Error"}


def image_format(path: Path) -> str:
    fmt = FORMATS.get(path.suffix.lower())
    if not fmt:
        raise InfrastructureError(
            msg=f"Kairon cannot boot {path.name}: use one of {', '.join(sorted(FORMATS))}"
        )
    return fmt


def sha256_file(path: Path, chunk: int = 4 << 20) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        while block := f.read(chunk):
            h.update(block)
    return h.hexdigest()


def vm_name_for(args, path: Path) -> str:
    raw = getattr(args, "kairon_vm_name", None) or getattr(args, "vm_name", None) or path.stem.split(".")[0]
    name = "".join(c if c.isalnum() else "-" for c in str(raw).lower()).strip("-")
    return name[:63].rstrip("-") or "imported-vm"


class _ImageServer:
    """Serve exactly one file at an unguessable path; everything else is 404."""

    def __init__(self, path: Path, bind: str) -> None:
        host, _, port = bind.rpartition(":")
        self.path = path
        self.route = f"/{secrets.token_urlsafe(18)}/{path.name}"
        self.completed = 0
        server = self

        class Handler(http.server.BaseHTTPRequestHandler):
            def _headers(self) -> bool:
                if self.path != server.route:
                    self.send_error(404)
                    return False
                self.send_response(200)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(server.path.stat().st_size))
                self.end_headers()
                return True

            def do_HEAD(self) -> None:
                self._headers()

            def do_GET(self) -> None:
                if not self._headers():
                    return
                with server.path.open("rb") as f:
                    shutil.copyfileobj(f, self.wfile, 4 << 20)
                server.completed += 1

            def log_message(self, fmt: str, *a: Any) -> None:
                pass

        self.httpd = http.server.ThreadingHTTPServer((host or "0.0.0.0", int(port)), Handler)
        self.port = self.httpd.server_address[1]
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)

    def __enter__(self) -> _ImageServer:
        self.thread.start()
        return self

    def __exit__(self, *exc: object) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()


class KaironDeployer:
    """Create a Kairon Machine from a converted disk via Veyron ``POST /api/v1/imports``."""

    def __init__(self, logger, args) -> None:
        self.logger = logger
        self.args = args
        self.veyron_url = (getattr(args, "kairon_veyron_url", None) or "").rstrip("/")
        self.api_key = getattr(args, "kairon_api_key", None) or os.environ.get("VEYRON_API_KEY")
        self.namespace = getattr(args, "kairon_namespace", None) or "default"
        self.timeout = int(getattr(args, "kairon_wait_timeout", None) or 1800)
        self._ssl = None
        if getattr(args, "kairon_insecure", False):
            self._ssl = ssl.create_default_context()
            self._ssl.check_hostname = False
            self._ssl.verify_mode = ssl.CERT_NONE

    def _api(self, method: str, path: str, body: dict | None = None) -> dict:
        req = urllib.request.Request(  # noqa: S310  # scheme checked in deploy()
            self.veyron_url + path,
            method=method,
            data=json.dumps(body).encode() if body is not None else None,
            headers={"Content-Type": "application/json", "X-API-Key": self.api_key or ""},
        )
        try:
            with urllib.request.urlopen(req, timeout=60, context=self._ssl) as resp:  # noqa: S310  # scheme checked in deploy()
                return json.loads(resp.read() or b"{}")
        except urllib.error.HTTPError as e:
            detail = e.read().decode(errors="replace")[:400]
            raise InfrastructureError(msg=f"Veyron {method} {path} -> HTTP {e.code}: {detail}") from e
        except urllib.error.URLError as e:
            raise InfrastructureError(msg=f"Veyron unreachable at {self.veyron_url}: {e.reason}") from e

    def payload(self, name: str, image_url: str, digest: str, fmt: str) -> dict[str, Any]:
        a = self.args
        body: dict[str, Any] = {
            "name": name,
            "namespace": self.namespace,
            "image_url": image_url,
            "sha256": digest,
            "format": fmt,
            "repair": bool(getattr(a, "kairon_repair", False)),
            "start": not getattr(a, "kairon_no_start", False),
            "secure_boot": bool(getattr(a, "kairon_secure_boot", False)),
            "tpm": bool(getattr(a, "kairon_tpm", False)),
            "source": {
                "tool": "h2kvm",
                "hypervisor": getattr(a, "kairon_source_hypervisor", None),
                "vm": getattr(a, "vm_name", None),
            },
        }
        if getattr(a, "kairon_cpus", None):
            body["cpus"] = int(a.kairon_cpus)
        if getattr(a, "kairon_memory", None):
            body["memory"] = str(a.kairon_memory)
        return body

    def _wait(self, name: str) -> str:
        deadline = time.monotonic() + self.timeout
        status = "Pending"
        while time.monotonic() < deadline:
            data = self._api("GET", f"/api/v1/imports/{self.namespace}/{name}").get("data", {})
            status = data.get("status") or status
            if status in FAILED:
                raise InfrastructureError(msg=f"Kairon Machine {self.namespace}/{name} is {status}")
            if status in SETTLED:
                return status
            time.sleep(5)
        raise InfrastructureError(
            msg=f"Kairon Machine {self.namespace}/{name} not Running after {self.timeout}s (last: {status})"
        )

    def deploy(self, image_path: str) -> dict[str, Any]:
        path = Path(image_path)
        if not path.is_file():
            raise InfrastructureError(msg=f"Image not found: {path}")
        if not self.veyron_url:
            raise InfrastructureError(msg="--deploy-kairon requires --kairon-veyron-url")
        if not self.veyron_url.startswith(("http://", "https://")):
            raise InfrastructureError(msg="--kairon-veyron-url must be an http:// or https:// URL")
        fmt = image_format(path)
        name = vm_name_for(self.args, path)
        image_url = getattr(self.args, "kairon_image_url", None)
        serve = getattr(self.args, "kairon_serve", None)
        advertise = (getattr(self.args, "kairon_advertise_url", None) or "").rstrip("/")
        start = not getattr(self.args, "kairon_no_start", False)
        if not image_url and not serve:
            raise InfrastructureError(
                msg="--deploy-kairon needs --kairon-image-url or --kairon-serve with --kairon-advertise-url"
            )
        if serve and not image_url:
            if not advertise:
                raise InfrastructureError(
                    msg="--kairon-serve needs --kairon-advertise-url (the base URL Kairon nodes reach)"
                )
            if not start:
                raise InfrastructureError(
                    msg="--kairon-serve needs the VM to start (Kairon fetches the image at first boot); "
                    "publish it and use --kairon-image-url for a stopped import"
                )

        if getattr(self.args, "dry_run", False):
            self.logger.info(
                "[dry-run] Would import %s into Kairon as %s/%s", path.name, self.namespace, name
            )
            return {"vm_name": name, "namespace": self.namespace, "format": fmt, "dry_run": True}

        self.logger.info("Hashing %s for the Kairon image cache key...", path.name)
        digest = sha256_file(path)

        if image_url:
            created = self._api("POST", "/api/v1/imports", self.payload(name, image_url, digest, fmt))
            status = self._wait(name) if start else created.get("data", {}).get("status", "Stopped")
        else:
            with _ImageServer(path, serve) as server:
                image_url = f"{advertise}{server.route}"
                self.logger.info("Serving %s on port %d for kairon-node", path.name, server.port)
                self._api("POST", "/api/v1/imports", self.payload(name, image_url, digest, fmt))
                status = self._wait(name)

        self.logger.info("Kairon Machine %s/%s is %s", self.namespace, name, status)
        return {
            "vm_name": name,
            "namespace": self.namespace,
            "format": fmt,
            "digest": f"sha256:{digest}",
            "status": status,
            "served": bool(serve) and not getattr(self.args, "kairon_image_url", None),
        }


def deploy_to_kairon(logger, args, image_path: str) -> dict[str, Any]:
    """Import a converted disk into Kairon through Veyron."""
    return KaironDeployer(logger, args).deploy(image_path)
