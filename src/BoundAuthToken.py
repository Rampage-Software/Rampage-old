import base64
import time
import httpc
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.backends import default_backend
import json
import hashlib

class BATGenerator():
    SEPARATOR = '|'

    def __init__(self):
        pass

    def hash_string_with_sha256(self, s: str) -> str:
        msg_bytes = s.encode('utf-8')
        hash_bytes = hashlib.sha256(msg_bytes).digest()
        return base64.b64encode(hash_bytes).decode('utf-8')

    def export_public_key_as_spki(self, public_key):
        spki_bytes = public_key.public_bytes(
            encoding=serialization.Encoding.DER,
            format=serialization.PublicFormat.SubjectPublicKeyInfo
        )
        return base64.b64encode(spki_bytes).decode('utf-8')

    def generate_signing_key_pair_unextractable(self):
        private_key = ec.generate_private_key(ec.SECP256R1(), default_backend())
        public_key = private_key.public_key()

        return private_key, public_key

    def sign(self, private_key, data:str):
        data_bytes = bytes(data, 'utf-8')
        signature = private_key.sign(data_bytes, ec.ECDSA(hashes.SHA256()))

        return base64.b64encode(signature).decode('utf-8')

    def generate_secure_auth_intent(self, user_agent, csrf_token, client):
        private_key, public_key = self.generate_signing_key_pair_unextractable()
        client_public_key = self.export_public_key_as_spki(public_key)
        client_epoch_timestamp = int(time.time())

        req_url = "https://apis.roblox.com/hba-service/v1/getServerNonce"
        req_headers = httpc.get_roblox_headers(user_agent, csrf_token)

        response = client.get(req_url, headers=req_headers)
        server_nonce = response.text.strip('"')
        payload = f"{client_public_key}{self.SEPARATOR}{str(client_epoch_timestamp)}{self.SEPARATOR}{server_nonce}"
        sai_signature = self.sign(private_key, payload)

        return {
            "clientEpochTimestamp": client_epoch_timestamp,
            "clientPublicKey": client_public_key,
            "saiSignature": sai_signature,
            "serverNonce": server_nonce
        }

    def generate_bound_auth_token(self, payload):
        private_key, public_key = self.generate_signing_key_pair_unextractable()

        client_epoch_timestamp = str(int(time.time()))

        if isinstance(payload, dict):
            str_to_hash = json.dumps(payload)
        elif isinstance(payload, str):
            str_to_hash = payload

        hashed_req_body = self.hash_string_with_sha256(str_to_hash)

        payload_to_sign = BATGenerator.SEPARATOR.join([hashed_req_body, client_epoch_timestamp])
        bat_signature = self.sign(private_key, payload_to_sign);

        return BATGenerator.SEPARATOR.join([hashed_req_body, str(client_epoch_timestamp), bat_signature])