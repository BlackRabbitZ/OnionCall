from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path

from onioncall.config import ConfigError, generate_secret, load_secret, secret_path, secret_token
from onioncall.session import safe_display
from onioncall.tor import TorError, validate_onion


class ConfigAndInputTests(unittest.TestCase):
    def test_secret_file_has_private_permissions(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory) / "home"
            key = generate_secret(home)
            self.assertEqual(load_secret(home), key)
            self.assertEqual(stat.S_IMODE(secret_path(home).stat().st_mode), 0o600)
            self.assertEqual(stat.S_IMODE(home.stat().st_mode), 0o700)

    def test_insecure_secret_permissions_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            generate_secret(home)
            os.chmod(secret_path(home), 0o644)
            with self.assertRaisesRegex(ConfigError, "Unsichere Rechte"):
                load_secret(home)

    def test_secret_token_does_not_accept_short_keys(self) -> None:
        with self.assertRaises(ConfigError):
            secret_token(b"short")

    def test_terminal_escape_characters_are_removed(self) -> None:
        output = safe_display("hallo\x1b]52;c;evil\x07")
        self.assertNotIn("\x1b", output)
        self.assertNotIn("\x07", output)

    def test_only_onion_v3_addresses_are_accepted(self) -> None:
        address = "a" * 56 + ".onion"
        self.assertEqual(validate_onion("https://" + address + "/"), address)
        for invalid in ("example.com", "a.onion", "$(touch /tmp/bad).onion"):
            with self.assertRaises(TorError):
                validate_onion(invalid)


if __name__ == "__main__":
    unittest.main()
