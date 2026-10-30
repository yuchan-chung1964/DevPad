"""Local stand-in for an identity provider's JWKS endpoint (what Supabase serves for its ES256 signing keys).

    python scripts/dev_jwks.py [port]     # default 9999; writes dev_jwt_private.pem next to this script

Then run the API with JWT_JWKS_URL=http://localhost:9999/jwks.json and the smoke test with
SMOKE_PRIVATE_KEY=scripts/dev_jwt_private.pem. Development only: the key is regenerated each run.
"""
import base64
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

port = int(sys.argv[1]) if len(sys.argv) > 1 else 9999
key = ec.generate_private_key(ec.SECP256R1())
pem_path = Path(__file__).with_name("dev_jwt_private.pem")
pem_path.write_bytes(key.private_bytes(
    serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()))


def b64(n: int) -> str:
    return base64.urlsafe_b64encode(n.to_bytes(32, "big")).rstrip(b"=").decode()


nums = key.public_key().public_numbers()
JWKS = json.dumps({"keys": [{"kty": "EC", "crv": "P-256", "alg": "ES256", "use": "sig", "kid": "dev-key",
                             "x": b64(nums.x), "y": b64(nums.y)}]}).encode()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(JWKS)

    def log_message(self, *_):
        pass


print(f"JWKS at http://localhost:{port}/jwks.json; private key in {pem_path}")
HTTPServer(("127.0.0.1", port), Handler).serve_forever()
