from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from onioncall.config import Config
from onioncall.tor import TorError, TorProcess, validate_loopback_host, validate_onion


class TorSecurityTests(unittest.TestCase):
    def test_direct_mode_rejects_external_ip(self):
        with self.assertRaises(TorError):
            validate_loopback_host('8.8.8.8')
        with self.assertRaises(TorError):
            validate_loopback_host('example.com')
        self.assertEqual(validate_loopback_host('127.0.0.1'), '127.0.0.1')
        self.assertEqual(validate_loopback_host('::1'), '::1')

    def test_client_torrc_contains_no_hidden_service(self):
        with tempfile.TemporaryDirectory() as tmp:
            tor = TorProcess(Config(), Path(tmp), service=False)
            tor._write_torrc()
            text = tor.torrc.read_text()
            self.assertNotIn('HiddenService', text)
            self.assertIn('SocksPort 127.0.0.1:', text)

    def test_service_torrc_binds_forward_only_to_loopback(self):
        with tempfile.TemporaryDirectory() as tmp:
            tor = TorProcess(Config(), Path(tmp), service=True)
            tor._write_torrc()
            text = tor.torrc.read_text()
            self.assertIn('HiddenServicePort 17777 127.0.0.1:17777', text)

    def test_onion_validation(self):
        good = 'a' * 56 + '.onion'
        self.assertEqual(validate_onion(good), good)
        with self.assertRaises(TorError):
            validate_onion('example.com')


if __name__ == '__main__':
    unittest.main()
