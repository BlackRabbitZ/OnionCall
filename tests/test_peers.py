from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from onioncall.config import ConfigError, generate_secret
from onioncall.peers import create_peer, list_peers, load_peer, pin_peer_fingerprint

FP1 = 'BRZ-' + '-'.join(['AAAA'] * 8)
FP2 = 'BRZ-' + '-'.join(['BBBB'] * 8)


class PeerTests(unittest.TestCase):
    def test_per_peer_keys_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            generate_secret(home)
            a = create_peer('alice', home=home)
            b = create_peer('bob', home=home)
            self.assertNotEqual(a.key, b.key)
            self.assertEqual(list_peers(home), ['alice', 'bob', 'default'])

    def test_fingerprint_pinning_detects_change(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            generate_secret(home)
            p = load_peer('default', home)
            pin_peer_fingerprint(p, FP1, home)
            p2 = load_peer('default', home)
            self.assertEqual(p2.fingerprint, FP1)
            with self.assertRaises(ConfigError):
                pin_peer_fingerprint(p2, FP2, home)


if __name__ == '__main__':
    unittest.main()
