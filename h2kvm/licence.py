# Copyright (c) 2026 ZyvorAI Labs Private Limited.
# SPDX-License-Identifier: LicenseRef-Zyvor-Production-2.0
# https://zyvor.dev · info@zyvor.dev

# h2kvm/licence.py
"""Soft licence status for h2kvm (ZYV1 Ed25519 keys, verify only, standard library only).

Key format shared by every Zyvor product: ZYV1.<b64url payload JSON>.<b64url Ed25519 signature over the payload bytes>.
Keys are issued by Zyvor; no issuing or signing code and no private key lives here.

Enforcement is soft: nothing in h2kvm is ever disabled, limited or deleted because there is no key or because a trial or
licence ended. The status is information only. A 30-day trial key (edition "trial") applies to the paid production licence
and support; free evaluation and non-production use under the Zyvor Production Licence is unchanged.

Key source: H2KVM_LICENCE_KEY, else the file named by H2KVM_LICENCE_FILE, else ~/.config/h2kvm/licence.key.
States: licensed | trial | licence_expired | unlicensed | invalid.
"""
import base64
import hashlib
import json
import os
import time
from pathlib import Path

PRODUCT = 'h2kvm'
PREFIX = 'ZYV1'
DAY = 86400
# Same text as zyvor-licensing/public-keys/h2kvm.pub (verify only).
PUBLIC_KEY = 'DCak8c3spUkuIEayUKXhQzYwTEGi4YBRdJnwigRsLqo'
DEFAULT_KEY_FILE = '~/.config/h2kvm/licence.key'

# --- Ed25519 verification (RFC 8032, section 5.1.7), standard library only ---------------------
_P = 2**255 - 19
_Q = 2**252 + 27742317777372353535851937790883648493
_D = -121665 * pow(121666, _P - 2, _P) % _P
_I = pow(2, (_P - 1) // 4, _P)


def _decode_point(s):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, 'little')
    sign = y >> 255
    y &= (1 << 255) - 1
    if y >= _P:
        return None
    x2 = (y * y - 1) * pow(_D * y * y + 1, _P - 2, _P) % _P
    if x2 == 0:
        if sign:
            return None
        x = 0
    else:
        x = pow(x2, (_P + 3) // 8, _P)
        if (x * x - x2) % _P:
            x = x * _I % _P
        if (x * x - x2) % _P:
            return None
        if (x & 1) != sign:
            x = _P - x
    return (x, y, 1, x * y % _P)


def _add(a, b):
    A = (a[1] - a[0]) * (b[1] - b[0]) % _P
    B = (a[1] + a[0]) * (b[1] + b[0]) % _P
    C = 2 * a[3] * b[3] * _D % _P
    D = 2 * a[2] * b[2] % _P
    E, F, G, H = B - A, D - C, D + C, B + A
    return (E * F % _P, G * H % _P, F * G % _P, E * H % _P)


def _mul(s, point):
    q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            q = _add(q, point)
        point = _add(point, point)
        s >>= 1
    return q


def _same(a, b):
    return (a[0] * b[2] - b[0] * a[2]) % _P == 0 and (a[1] * b[2] - b[1] * a[2]) % _P == 0


_BASE = _decode_point(bytes([0x58]) + bytes([0x66]) * 31)


def ed25519_verify(public, message, signature):
    if len(public) != 32 or len(signature) != 64:
        return False
    a = _decode_point(public)
    r = _decode_point(signature[:32])
    if a is None or r is None:
        return False
    s = int.from_bytes(signature[32:], 'little')
    if s >= _Q:
        return False
    h = int.from_bytes(hashlib.sha512(signature[:32] + public + message).digest(), 'little') % _Q
    return _same(_mul(s, _BASE), _add(r, _mul(h, a)))


# --- key parsing and status ----------------------------------------------------------------------
def _unb64(text):
    return base64.urlsafe_b64decode(text + '=' * (-len(text) % 4))


def _parse(key, public):
    """Return (payload, None) for a key signed by `public` for this product, else (None, reason). Expiry is not checked."""
    try:
        prefix, body, sig = key.strip().split('.')
        if prefix != PREFIX:
            return None, 'not a Zyvor licence key'
        raw = _unb64(body)
        if not ed25519_verify(_unb64(public), raw, _unb64(sig)):
            return None, 'signature does not verify'
        payload = json.loads(raw)
    except Exception:
        return None, 'could not read the key'
    if not isinstance(payload, dict) or payload.get('v') != 1 or payload.get('product') != PRODUCT:
        return None, 'key is for a different product'
    return payload, None


def evaluate(key, now=None, public=PUBLIC_KEY):
    """Pure status for `key` (None or empty means no key). Never raises and never gates anything."""
    now = int(time.time() if now is None else now)
    out = {'product': PRODUCT, 'enforcement': 'soft', 'state': 'unlicensed', 'edition': None, 'days_left': None, 'message':
           'No licence key. h2kvm keeps working; a 30-day trial key for the paid production licence and support is available from sales@zyvor.dev.'}
    if not key or not key.strip():
        return out
    payload, why = _parse(key, public)
    if payload is None:
        out.update(state='invalid', message='Licence key not accepted (%s). h2kvm keeps working.' % why)
        return out
    try:
        expires = int(payload.get('expires', 0))
    except (TypeError, ValueError):
        out.update(state='invalid', message='Licence key not accepted (bad expiry). h2kvm keeps working.')
        return out
    left = max(0, (expires - now) // DAY)
    out.update(edition=payload.get('edition'), days_left=left, expires=expires, licensee=payload.get('licensee'))
    if now >= expires:
        out.update(state='licence_expired', message='Licence ended. h2kvm keeps working; contact sales@zyvor.dev to renew.')
    elif payload.get('edition') == 'trial':
        out.update(state='trial', message='30-day trial key, %d day(s) left. Nothing is disabled when it ends.' % left)
    else:
        out.update(state='licensed', message='Licensed, %d day(s) left.' % left)
    return out


def _load_key():
    key = os.environ.get('H2KVM_LICENCE_KEY', '').strip()
    if key:
        return key
    path = Path(os.environ.get('H2KVM_LICENCE_FILE') or DEFAULT_KEY_FILE).expanduser()
    try:
        return path.read_text().strip() or None
    except OSError:
        return None


def status(now=None):
    """Current licence status from the environment and files."""
    return evaluate(_load_key(), now)
