"""InfrastructureError raised by the libvirt managers must carry the message.

H2KvmError is a dataclass whose first positional field is the numeric exit
code, so ``InfrastructureError("text")`` used to drop the text (str(e) was
"error"). The managers now pass ``msg=`` explicitly.
"""

from unittest.mock import patch

import pytest

from h2kvm.core.exceptions import InfrastructureError
from h2kvm.libvirt.libvirt_manager import LibvirtManager
from h2kvm.libvirt.pool_manager import PoolManager


def test_libvirt_manager_unavailable_message():
    with (
        patch("h2kvm.libvirt.libvirt_manager.LIBVIRT_AVAILABLE", False),
        pytest.raises(InfrastructureError) as exc,
    ):
        LibvirtManager()
    assert "libvirt Python bindings not available" in str(exc.value)
    assert exc.value.msg.startswith("libvirt Python bindings")


def test_pool_manager_unavailable_message():
    with (
        patch("h2kvm.libvirt.pool_manager.LIBVIRT_AVAILABLE", False),
        pytest.raises(InfrastructureError) as exc,
    ):
        PoolManager()
    assert "libvirt Python bindings not available" in str(exc.value)


def test_define_domain_missing_xml_message(tmp_path):
    with patch("h2kvm.libvirt.libvirt_manager.LIBVIRT_AVAILABLE", True):
        mgr = LibvirtManager()
    mgr.conn = object()  # skip connect()
    with pytest.raises(InfrastructureError) as exc:
        mgr.define_domain(tmp_path / "missing.xml")
    assert "Domain XML not found" in str(exc.value)
