from __future__ import annotations

import base64
import hashlib
import unittest

from onioncall.tor import TorError, validate_loopback_host, validate_onion

def valid_onion() -> str:
    public = bytes(range(32))
    version = b"\x03"
    checksum = hashlib.sha3_256(b".onion checksum" + public + version).digest()[:2]
    return base64.b32encode(public + checksum + version).decode("ascii").lower() + ".onion"


class TorValidationTests(unittest.TestCase):
    def test_accepts_valid_v3_checksum(self) -> None:
        onion = valid_onion()
        self.assertEqual(validate_onion(onion), onion)

    def test_rejects_bad_v3_checksum(self) -> None:
        onion = valid_onion()
        replacement = "a" if onion[0] != "a" else "b"
        with self.assertRaises(TorError):
            validate_onion(replacement + onion[1:])

    def test_loopback_matches_documented_literals_exactly(self) -> None:
        self.assertEqual(validate_loopback_host("127.0.0.1"), "127.0.0.1")
        self.assertEqual(validate_loopback_host("::1"), "::1")
        with self.assertRaises(TorError):
            validate_loopback_host("127.0.0.2")


if __name__ == "__main__":
    unittest.main()
