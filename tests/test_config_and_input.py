from __future__ import annotations

import os
import stat
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from onioncall.cli import _address_for_menu, main
from onioncall.config import (
    ConfigError,
    generate_secret,
    load_config,
    load_secret,
    parse_secret,
    secret_path,
    secret_token,
)
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

    def test_set_secret_prompts_without_command_line_token(self) -> None:
        replacement = b"r" * 32
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.dict(os.environ, {"ONIONCALL_HOME": directory}),
        ):
            self.assertEqual(main(["init"]), 0)
            with mock.patch("onioncall.cli.getpass.getpass", return_value=secret_token(replacement)) as prompt:
                self.assertEqual(main(["set-secret", "--replace"]), 0)
            prompt.assert_called_once()
            self.assertEqual(load_secret(Path(directory)), replacement)

    def test_set_secret_rejects_command_line_values(self) -> None:
        token = secret_token(b"r" * 32)
        for arguments in (
            ["set-secret", token, "--replace"],
            ["set-secret", "--replace", "onioncall", "set-secret", "--replace"],
        ):
            with self.subTest(arguments=arguments), self.assertRaises(SystemExit):
                main(arguments)

    def test_terminal_menu_can_be_opened_explicitly(self) -> None:
        with mock.patch("builtins.input", return_value="0"):
            self.assertEqual(main(["menu"]), 0)

    def test_no_subcommand_opens_gui(self) -> None:
        with mock.patch("onioncall.cli.run_gui", return_value=0) as gui:
            self.assertEqual(main([]), 0)
        gui.assert_called_once_with()

    def test_menu_remembers_last_valid_address(self) -> None:
        address = "a" * 56 + ".onion"
        with (
            tempfile.TemporaryDirectory() as directory,
            mock.patch.dict(os.environ, {"ONIONCALL_HOME": directory}),
            mock.patch("builtins.input", return_value=address),
        ):
            self.assertEqual(_address_for_menu(), address)
            self.assertEqual(load_config(Path(directory)).last_address, address)

    def test_onion_address_is_rejected_as_secret(self) -> None:
        with self.assertRaisesRegex(ConfigError, "Onion-Adresse"):
            parse_secret("a" * 56 + ".onion")

    def test_terminal_escape_characters_are_removed(self) -> None:
        output = safe_display("hallo\x1b]52;c;evil\x07")
        self.assertNotIn("\x1b", output)
        self.assertNotIn("\x07", output)

    def test_only_onion_v3_addresses_are_accepted(self) -> None:
        address = "a" * 56 + ".onion"
        self.assertEqual(validate_onion("https://" + address + "/"), address)
        with self.assertRaisesRegex(TorError, "Verbindungsschlüssel"):
            validate_onion(secret_token(b"r" * 32))
        for invalid in ("example.com", "a.onion", "$(touch /tmp/bad).onion"):
            with self.assertRaises(TorError):
                validate_onion(invalid)


if __name__ == "__main__":
    unittest.main()
