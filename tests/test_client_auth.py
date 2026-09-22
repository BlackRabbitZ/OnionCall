from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from onioncall.client_auth import (
    generate_authorized_client,
    list_server_authorizations,
    parse_private_token,
)

class AuthTests(unittest.TestCase):
    def test_generate(self):
        with tempfile.TemporaryDirectory() as tmp:
            home=Path(tmp); token=generate_authorized_client('laptop',home)
            self.assertTrue(token.startswith('onioncall:tor-auth:v1:')); self.assertIn('laptop',list_server_authorizations(home)); self.assertTrue(parse_private_token(token))
if __name__=='__main__': unittest.main()
