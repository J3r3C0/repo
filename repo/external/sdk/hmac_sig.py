import hmac, hashlib, time, json
from typing import Dict, Any

def make_headers(secret: bytes, token: str, body: Dict[str, Any]) -> Dict[str, str]:
    ts = str(int(time.time()))
    body_bytes = json.dumps(body, separators=(',', ':')).encode()
    msg = ts.encode() + b"." + body_bytes
    sig = hmac.new(secret, msg, hashlib.sha256).hexdigest()
    return {
        "Authorization": f"Bearer {token}",
        "X-Sheratan-Timestamp": ts,
        "X-Sheratan-Idempotency": body.get("job_id", "na"),
        "X-Sheratan-Signature": f"sha256={sig}",
        "Content-Type": "application/json",
    }
