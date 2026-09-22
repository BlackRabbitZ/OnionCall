from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from onioncall.config import generate_secret
from onioncall.peers import create_peer, list_peers, load_peer, peer_secret_token, import_peer_secret, pin_peer_fingerprint

class PeerTests(unittest.TestCase):
    def test_profiles(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp); generate_secret(home); p=create_peer('alice',home=home); token=peer_secret_token(p)
            self.assertIn('default',list_peers(home)); self.assertIn('alice',list_peers(home)); self.assertEqual(import_peer_secret('bob',token,home=home).key,p.key)
            fp='BRZ-'+'-'.join(['ABCD']*8); pin_peer_fingerprint(load_peer('alice',home),fp,home); self.assertEqual(load_peer('alice',home).fingerprint,fp)
if __name__=='__main__': unittest.main()
