# Copyright (c) 2026 ZyvorAI Labs Private Limited.
# SPDX-License-Identifier: LicenseRef-Zyvor-Production-1.0
# https://zyvor.dev · info@zyvor.dev

# h2kvm/vmware/transports/__init__.py
"""
VMware transport/download mechanisms.

This package provides various transport methods for downloading VM data:
- http_client: HTTPS download client
- http_progress: Progress reporters for HTTP downloads
- ovftool_client: VMware ovftool-based transport
- ovftool_loader: ovftool binary loader
- govc_common: Common govc utility functions
- govc_export: govc-based export functionality
- hyperctl_common: hypersdk daemon integration (NEW)
"""

# Try to import hyperctl support
try:
    from .hyperctl_common import (
        HyperCtlRunner,
        create_hyperctl_runner,
        export_vm_hyperctl,
    )

    HYPERCTL_AVAILABLE = True
except ImportError:
    HYPERCTL_AVAILABLE = False
    # optional-import fallback: callers must check HYPERCTL_AVAILABLE before using these names
    HyperCtlRunner = None  # type: ignore[assignment,misc]
    create_hyperctl_runner = None  # type: ignore[assignment]
    export_vm_hyperctl = None  # type: ignore[assignment]

__all__ = [
    "HYPERCTL_AVAILABLE",
    "HyperCtlRunner",
    "create_hyperctl_runner",
    "export_vm_hyperctl",
]
