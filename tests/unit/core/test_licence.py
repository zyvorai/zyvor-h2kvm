# Copyright (c) 2026 ZyvorAI Labs Private Limited.
# SPDX-License-Identifier: LicenseRef-Zyvor-Production-1.0
# https://zyvor.dev · info@zyvor.dev
"""Soft licence status: trial valid, expired, wrong product, tampered. Uses a throwaway keypair (signing helper is test-only)."""
import base64
import hashlib
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from h2kvm import licence

NOW = 1_800_000_000


def _b64(raw):
    return base64.urlsafe_b64encode(raw).rstrip(b'=').decode()


def _enc(pt):
    zi = pow(pt[2], licence._P - 2, licence._P)
    x, y = pt[0] * zi % licence._P, pt[1] * zi % licence._P
    return (y | ((x & 1) << 255)).to_bytes(32, 'little')


def _keypair(seed):
    h = hashlib.sha512(seed).digest()
    a = int.from_bytes(h[:32], 'little')
    a &= (1 << 254) - 8
    a |= 1 << 254
    return a, h[32:], _enc(licence._mul(a, licence._BASE))


def _sign(seed, msg):
    a, prefix, pub = _keypair(seed)
    r = int.from_bytes(hashlib.sha512(prefix + msg).digest(), 'little') % licence._Q
    big_r = _enc(licence._mul(r, licence._BASE))
    k = int.from_bytes(hashlib.sha512(big_r + pub + msg).digest(), 'little') % licence._Q
    return big_r + ((r + k * a) % licence._Q).to_bytes(32, 'little')


def _key(seed, product='h2kvm', edition='trial', expires=NOW + 30 * 86400):
    payload = json.dumps({'v': 1, 'product': product, 'edition': edition, 'id': 't', 'licensee': 'x',
                          'email': 'x@example.com', 'macs': 1, 'issued': NOW, 'expires': expires}, separators=(',', ':')).encode()
    return 'ZYV1.%s.%s' % (_b64(payload), _b64(_sign(seed, payload)))


SEED, OTHER = b'\x07' * 32, b'\x09' * 32
PUB = _b64(_keypair(SEED)[2])


class LicenceTests(unittest.TestCase):
    def test_rfc8032_vector_and_embedded_key(self):
        pub = bytes.fromhex('d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a')
        sig = bytes.fromhex('e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b')
        self.assertTrue(licence.ed25519_verify(pub, b'', sig))
        self.assertEqual(len(licence._unb64(licence.PUBLIC_KEY)), 32)

    def test_trial_is_valid_and_counts_down(self):
        s = licence.evaluate(_key(SEED), NOW + 10 * 86400, PUB)
        self.assertEqual((s['state'], s['edition'], s['days_left'], s['enforcement']), ('trial', 'trial', 20, 'soft'))

    def test_pro_is_licensed(self):
        self.assertEqual(licence.evaluate(_key(SEED, edition='pro'), NOW + 86400, PUB)['state'], 'licensed')

    def test_expired_is_soft(self):
        s = licence.evaluate(_key(SEED), NOW + 31 * 86400, PUB)
        self.assertEqual((s['state'], s['days_left']), ('licence_expired', 0))
        self.assertIn('keeps working', s['message'])

    def test_wrong_product_wrong_signer_tampered_garbage(self):
        self.assertEqual(licence.evaluate(_key(SEED, product='netra'), NOW, PUB)['state'], 'invalid')
        self.assertEqual(licence.evaluate(_key(OTHER), NOW, PUB)['state'], 'invalid')
        k = _key(SEED)
        head, body, sig = k.split('.')
        raw = json.loads(base64.urlsafe_b64decode(body + '=='))
        raw['edition'] = 'pro'
        forged = '%s.%s.%s' % (head, _b64(json.dumps(raw, separators=(',', ':')).encode()), sig)
        self.assertEqual(licence.evaluate(forged, NOW, PUB)['state'], 'invalid')
        self.assertEqual(licence.evaluate(k + 'A', NOW, PUB)['state'], 'invalid')
        self.assertEqual(licence.evaluate('garbage', NOW, PUB)['state'], 'invalid')
        # the real embedded public key refuses a key signed by the throwaway key
        self.assertEqual(licence.evaluate(k, NOW)['state'], 'invalid')

    def test_no_key_is_unlicensed_and_status_reads_env_then_file(self):
        self.assertEqual(licence.evaluate(None, NOW, PUB)['state'], 'unlicensed')
        self.assertEqual(licence.evaluate('  ', NOW, PUB)['state'], 'unlicensed')
        with tempfile.TemporaryDirectory() as d, patch.dict(os.environ, {'H2KVM_LICENCE_KEY': '', 'H2KVM_LICENCE_FILE': str(Path(d) / 'none')}):
            self.assertEqual(licence.status(NOW)['state'], 'unlicensed')
            Path(d, 'licence.key').write_text('garbage')
            os.environ['H2KVM_LICENCE_FILE'] = str(Path(d) / 'licence.key')
            self.assertEqual(licence.status(NOW)['state'], 'invalid')
            os.environ['H2KVM_LICENCE_KEY'] = ''


if __name__ == '__main__':
    unittest.main()
