import json
import sys
import base64
import nacl.signing
import nacl.encoding

def sign_payload(payload_b64, private_key_hex):
    payload_str = base64.b64decode(payload_b64).decode('utf-8')
    payload = json.loads(payload_str)
    # Canonical JSON (sorted keys, no spaces)
    content = {k: v for k, v in payload.items() if k != "signature"}
    canonical_json = json.dumps(content, sort_keys=True, separators=(',', ':'))
    # sys.stderr.write(f"[debug] signing json: {canonical_json}\n")
    
    signing_key = nacl.signing.SigningKey(private_key_hex, encoder=nacl.encoding.HexEncoder)
    signature = signing_key.sign(canonical_json.encode('utf-8')).signature
    return signature.hex()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python sign_test.py '<json_payload>' <private_key_hex>")
        sys.exit(1)
    
    print(sign_payload(sys.argv[1], sys.argv[2]))
