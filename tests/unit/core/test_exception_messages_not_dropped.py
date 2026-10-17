"""H2KvmError subclasses are dataclasses whose first positional field is the exit code.

Passing the message positionally used to store it in ``code`` and leave
``msg == "error"``; call sites must use ``msg=``.
"""

import pytest

from h2kvm.core.exceptions import VMwareError
from h2kvm.providers.vmware.utils.datastore import parse_backing_filename


def test_vmware_error_from_datastore_carries_message():
    with pytest.raises(VMwareError) as exc:
        parse_backing_filename("not-a-datastore-path")
    assert "Could not parse backing filename" in str(exc.value)
    assert exc.value.msg != "error"


def test_positional_string_would_have_been_dropped():
    # Documents the pitfall the msg= keyword avoids.
    assert str(VMwareError("boom")) == "error"
    assert str(VMwareError(msg="boom")) == "boom"
