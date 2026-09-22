from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from onioncall.config import generate_secret
from onioncall.peers import (
    create_peer,
    import_peer_secret,
    list_peers,
    load_peer,
    peer_secret_token,
    pin_peer_fingerprint,
)


class PeerTests(unittest.TestCase):
    def test_profiles(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            generate_secret(home)
            peer = create_peer("alice", home=home)
            token = peer_secret_token(peer)

            self.assertIn("default", list_peers(home))
            self.assertIn("alice", list_peers(home))
            self.assertEqual(import_peer_secret("bob", token, home=home).key, peer.key)

            fingerprint = "BRZ-" + "-".join(["ABCD"] * 8)
            pin_peer_fingerprint(load_peer("alice", home), fingerprint, home)
            self.assertEqual(load_peer("alice", home).fingerprint, fingerprint)


if __name__ == "__main__":
    unittest.main()
