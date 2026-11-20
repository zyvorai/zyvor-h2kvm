"""create_domain_rejoin_script only embeds credentials when both are present."""

import logging

from h2kvm.platforms.windows.active_directory import ActiveDirectoryManager

_INFO = {"domain_name": "corp.example", "computer_name": "WIN01", "ou_path": None}


def _mgr():
    return ActiveDirectoryManager(logging.getLogger("t"))


def test_partial_credentials_fall_back_to_interactive_script():
    script = _mgr().create_domain_rejoin_script(_INFO, credentials={"username": "admin"})
    assert "None" not in script
    assert "corp.example" in script


def test_full_credentials_embedded():
    script = _mgr().create_domain_rejoin_script(
        _INFO, credentials={"username": "admin", "password": "s3cret"}
    )
    assert "admin" in script
