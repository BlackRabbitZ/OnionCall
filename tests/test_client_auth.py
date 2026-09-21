from __future__ import annotations
import tempfile, unittest
from pathlib import Path
from onioncall.client_auth import generate_authorized_client, import_client_authorization, list_client_authorizations, list_server_authorizations, prepare_service_authorizations
from onioncall.config import Config
from onioncall.tor import TorProcess
class ClientAuthorizationTests(unittest.TestCase):
    def test_generate_and_import(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp); token=generate_authorized_client('alice',home); self.assertTrue(token.startswith('onioncall:tor-auth:v1:')); self.assertEqual(list_server_authorizations(home),['alice']); path=import_client_authorization('a'*56+'.onion',token,name='service-a',home=home); self.assertTrue(path.read_text().startswith('a'*56+':descriptor:x25519:')); self.assertEqual(list_client_authorizations(home),['service-a'])
    def test_service_auth_sync(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp); generate_authorized_client('bob',home); hidden=home/'hidden'; hidden.mkdir(); self.assertEqual(prepare_service_authorizations(hidden,home),1); self.assertTrue((hidden/'authorized_clients'/'bob.auth').exists())
    def test_client_torrc_uses_auth_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp); token=generate_authorized_client('bob',home); import_client_authorization('b'*56+'.onion',token,name='bob-service',home=home); tor=TorProcess(Config(),home,service=False); tor._write_torrc(); self.assertIn('ClientOnionAuthDir',tor.torrc.read_text())
if __name__=='__main__': unittest.main()
