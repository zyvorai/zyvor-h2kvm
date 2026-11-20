# Copyright (c) 2026 ZyvorAI Labs Private Limited.
# SPDX-License-Identifier: LicenseRef-Zyvor-Production-1.0
# https://zyvor.dev · info@zyvor.dev

# h2kvm/core/xml_utils.py
"""Shared XML escaping and manipulation utilities

Provides common helpers for XML escaping to avoid duplication across modules.
Uses xml.sax.saxutils for standard escaping with additional entity support.
"""

from __future__ import annotations

import xml.etree.ElementTree as ET
from typing import TYPE_CHECKING
from xml.sax.saxutils import escape as _sax_escape

if TYPE_CHECKING:
    from pathlib import Path


def parse_xml_root(path: Path) -> ET.Element:
    """Parse an XML file and return its root element.

    Uses ``defusedxml`` (mitigates entity-expansion DoS) when it is installed and falls
    back to the standard library parser otherwise.

    Raises:
        xml.etree.ElementTree.ParseError: malformed XML (including an empty document)
        OSError: the file cannot be read
    """
    root: ET.Element | None
    try:
        # pylint: disable-next=import-outside-toplevel  # optional hardening dependency; stdlib parser is the fallback
        from defusedxml.ElementTree import parse as safe_parse
    except ImportError:
        root = ET.parse(path).getroot()
    else:
        root = safe_parse(path).getroot()
    if root is None:
        raise ET.ParseError("XML document has no root element")
    return root


def xml_escape(s: object) -> str:
    """Escape string for XML text and attribute contexts.

    Args:
        s: Object to escape (will be converted to string)

    Returns:
        Escaped XML string with &, <, >, ', " encoded as entities

    Note:
        Safe for both XML text content and attribute values.
        Uses standard library xml.sax.saxutils.escape internally.

    Example:
        >>> xml_escape("a < b & c > d")
        'a &lt; b &amp; c &gt; d'
        >>> xml_escape('say "hello"')
        'say &quot;hello&quot;'
    """
    return _sax_escape(str(s), entities={"'": "&apos;", '"': "&quot;"})


def xml_escape_attr(s: str) -> str:
    """Escape string specifically for XML attribute values.

    Args:
        s: String to escape

    Returns:
        Escaped XML attribute string

    Note:
        Escapes &, <, >, ', " characters.
        Order matters: & must be escaped first to avoid double-escaping.

    Example:
        >>> xml_escape_attr('path="/tmp/file with spaces"')
        'path=&quot;/tmp/file with spaces&quot;'
    """
    return (
        s.replace("&", "&amp;")
        .replace("'", "&apos;")
        .replace('"', "&quot;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def xml_escape_text(s: str) -> str:
    """Escape string specifically for XML text content.

    Args:
        s: String to escape

    Returns:
        Escaped XML text string

    Note:
        Escapes &, <, > characters.
        Order matters: & must be escaped first to avoid double-escaping.
        Does not escape quotes since they don't need escaping in text content.

    Example:
        >>> xml_escape_text("a < b & c > d")
        'a &lt; b &amp; c &gt; d'
    """
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


__all__ = [
    "parse_xml_root",
    "xml_escape",
    "xml_escape_attr",
    "xml_escape_text",
]
