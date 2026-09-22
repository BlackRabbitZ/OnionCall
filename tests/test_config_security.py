from __future__ import annotations

import base64
import os
import secrets
import tempfile
import unittest
from pathlib import Path

from onioncall.config import ConfigError, generate_secret, import_secret, load_secret, parse_secret, secret_token


class ConfigSecurityTests(unittest.TestCase):
    def test_generated_secret_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            key = generate_secret(home)
            self.assertEqual(load_secret(home), key)

    def test_manual_raw_base64_import_is_rejected(self) -> None:
        raw = base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ConfigError):
                import_secret(raw, Path(tmp))

    def test_obviously_weak_versioned_key_is_rejected(self) -> None:
        weak = secret_token(b"A" * 32)
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ConfigError):
                import_secret(weak, Path(tmp))

    def test_random_onioncall_token_is_accepted(self) -> None:
        key = secrets.token_bytes(32)
        self.assertEqual(parse_secret(secret_token(key), require_token=True), key)

    @unittest.skipIf(os.name == "nt", "POSIX permission test")
    def test_unsafe_key_permissions_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            generate_secret(home)
            path = home / "conversation.key"
            path.chmod(0o644)
            with self.assertRaises(ConfigError):
                load_secret(home)


if __name__ == "__main__":
    unittest.main()
