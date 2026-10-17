"""parse_xml_root: shared safe XML root parsing for OVF / libvirt domain XML."""

import xml.etree.ElementTree as ET

import pytest

from h2kvm.core.xml_utils import parse_xml_root


def test_parse_returns_root(tmp_path):
    p = tmp_path / "a.xml"
    p.write_text("<domain><name>vm1</name></domain>")
    root = parse_xml_root(p)
    assert root.tag == "domain"
    assert root.findtext("name") == "vm1"


def test_malformed_xml_raises_parse_error(tmp_path):
    p = tmp_path / "bad.xml"
    p.write_text("<domain><name></domain>")
    with pytest.raises(ET.ParseError):
        parse_xml_root(p)


def test_missing_file_raises_oserror(tmp_path):
    with pytest.raises(OSError):
        parse_xml_root(tmp_path / "nope.xml")
