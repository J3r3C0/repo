import os
import json
import nacl.signing
import nacl.encoding
from pathlib import Path

IDENTITY_FILE = Path("data/node_identity.json")

def get_or_generate_identity():
    """
    Load or create a persistent Ed25519 keypair for the node.
    Returns (private_key_hex, public_key_hex)
    """
    if IDENTITY_FILE.exists():
        with open(IDENTITY_FILE, "r") as f:
            data = json.load(f)
            return data["private_key"], data["public_key"]
    
    # Generate new keypair
    signing_key = nacl.signing.SigningKey.generate()
    priv = signing_key.encode(encoder=nacl.encoding.HexEncoder).decode()
    pub = signing_key.verify_key.encode(encoder=nacl.encoding.HexEncoder).decode()
    
    IDENTITY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(IDENTITY_FILE, "w") as f:
        json.dump({"private_key": priv, "public_key": pub}, f)
    
    print(f"[identity] Generated new Ed25519 keypair. PubKey: {pub[:8]}...")
    return priv, pub

def sign_heartbeat(payload: dict, private_key_hex: str) -> str:
    """
    Produce Ed25519 signature over canonical JSON of the payload.
    Excludes existing 'signature' field if present.
    """
    signing_key = nacl.signing.SigningKey(private_key_hex, encoder=nacl.encoding.HexEncoder)
    # Canonical JSON (sorted keys, no spaces)
    content = {k: v for k, v in payload.items() if k != "signature"}
    canonical_json = json.dumps(content, sort_keys=True, separators=(',', ':'))
    
    signature = signing_key.sign(canonical_json.encode('utf-8')).signature
    return signature.hex()
