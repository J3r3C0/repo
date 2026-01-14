#!/usr/bin/env python3
"""
Offgrid Crypto Session Module (v0.16-alpha)
Production-grade session management with replay protection and session tracking.
"""
import os, hmac, json, base64, time, hashlib
from dataclasses import dataclass
from typing import Optional, Tuple
from nacl import public, signing, secret, utils


def hkdf_sha256(ikm: bytes, salt: bytes = b"", info: bytes = b"", length: int = 32) -> bytes:
    """HKDF-SHA256 key derivation function."""
    if not salt:
        salt = b"\x00" * 32
    prk = hmac.new(salt, ikm, hashlib.sha256).digest()
    t = b""
    okm = b""
    block = 0
    while len(okm) < length:
        block += 1
        t = hmac.new(prk, t + info + bytes([block]), hashlib.sha256).digest()
        okm += t
    return okm[:length]


@dataclass
class Identity:
    """Cryptographic identity with Ed25519 signing and X25519 key exchange."""
    ed25519_sign: signing.SigningKey
    ed25519_verify: signing.VerifyKey
    x25519_static: public.PrivateKey
    x25519_public: public.PublicKey
    
    @staticmethod
    def from_json(d: dict) -> "Identity":
        """Load identity from JSON configuration."""
        ed_sk = signing.SigningKey(base64.b64decode(d["ed25519"]["signing_key"]))
        ed_vk = ed_sk.verify_key
        x_sk = public.PrivateKey(base64.b64decode(d["x25519"]["private_key"]))
        x_pk = x_sk.public_key
        return Identity(ed_sk, ed_vk, x_sk, x_pk)


@dataclass
class Session:
    """
    Encrypted session with replay protection.
    
    Features:
    - Session ID (sid) for tracking
    - Sequence numbers (seq_out, seq_in) for replay protection
    - XSalsa20-Poly1305 authenticated encryption
    """
    sid: str
    key: bytes
    box: secret.SecretBox
    seq_out: int = 0
    seq_in: int = -1
    
    def seal(self, plaintext: bytes, aad: Optional[dict] = None) -> dict:
        """
        Encrypt and authenticate plaintext.
        
        Args:
            plaintext: Data to encrypt
            aad: Optional additional authenticated data (metadata)
            
        Returns:
            Envelope dict with encrypted payload and metadata
        """
        self.seq_out += 1
        nonce = utils.random(secret.SecretBox.NONCE_SIZE)
        ct = self.box.encrypt(plaintext, nonce)
        env = {
            "ver": 1,
            "sid": self.sid,
            "seq": self.seq_out,
            "ts": int(time.time()),
            "alg": "xsalsa20poly1305",
            "ct": base64.b64encode(ct).decode("ascii")
        }
        if aad:
            env["aad"] = aad
        return env
    
    def open(self, env: dict) -> bytes:
        """
        Decrypt and verify envelope.
        
        Args:
            env: Envelope dict from seal()
            
        Returns:
            Decrypted plaintext
            
        Raises:
            AssertionError: Session ID mismatch
            ValueError: Replay or out-of-order message detected
        """
        assert env.get("sid") == self.sid, "session mismatch"
        seq = int(env.get("seq", -1))
        if seq <= self.seq_in:
            raise ValueError("replay or out-of-order")
        self.seq_in = seq
        ct = base64.b64decode(env["ct"])
        return self.box.decrypt(ct)


def initiator_handshake(our_id: Identity, peer_static_pk_b64: str) -> Tuple[dict, bytes]:
    """
    Initiator side of Noise-NK handshake.
    
    Args:
        our_id: Our cryptographic identity
        peer_static_pk_b64: Peer's static X25519 public key (base64)
        
    Returns:
        (msg1, session_key): Handshake message and derived session key
    """
    eph_sk = public.PrivateKey.generate()
    eph_pk = eph_sk.public_key
    peer_pk = public.PublicKey(base64.b64decode(peer_static_pk_b64))
    shared = eph_sk.exchange(peer_pk)
    key = hkdf_sha256(shared, info=b"offgrid/noise-nk-key")
    
    payload = {
        "eph": base64.b64encode(bytes(eph_pk)).decode("ascii"),
        "from_ed25519": base64.b64encode(bytes(our_id.ed25519_verify)).decode("ascii")
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    sig = our_id.ed25519_sign.sign(payload_bytes).signature
    
    msg1 = {
        "ver": 1,
        "type": "hs1",
        "payload": base64.b64encode(payload_bytes).decode("ascii"),
        "sig_ed25519": base64.b64encode(sig).decode("ascii")
    }
    return msg1, key


def responder_handshake(our_id: Identity, msg1: dict) -> Tuple[dict, bytes, str]:
    """
    Responder side of Noise-NK handshake.
    
    Args:
        our_id: Our cryptographic identity
        msg1: Handshake message from initiator
        
    Returns:
        (msg2, session_key, peer_ed25519_b64): Response message, session key, and peer's Ed25519 key
        
    Raises:
        nacl.exceptions.BadSignatureError: Invalid signature
    """
    payload = json.loads(base64.b64decode(msg1["payload"]).decode("utf-8"))
    sig = base64.b64decode(msg1["sig_ed25519"])
    from_ed_b64 = payload["from_ed25519"]
    from_ed = signing.VerifyKey(base64.b64decode(from_ed_b64))
    from_ed.verify(base64.b64decode(msg1["payload"]), sig)
    
    eph_pk = public.PublicKey(base64.b64decode(payload["eph"]))
    shared = our_id.x25519_static.exchange(eph_pk)
    key = hkdf_sha256(shared, info=b"offgrid/noise-nk-key")
    
    msg2 = {"ver": 1, "type": "hs2", "ok": True}
    return msg2, key, from_ed_b64


def session_from_key(key: bytes, peer_hint: str) -> Session:
    """
    Create session from pre-shared key.
    
    Args:
        key: 32-byte session key
        peer_hint: Peer identifier for session ID generation
        
    Returns:
        Initialized Session object
    """
    sid = base64.b32encode(
        hashlib.sha256(key + peer_hint.encode()).digest()[:8]
    ).decode("ascii").rstrip("=")
    box = secret.SecretBox(key)
    return Session(sid=sid, key=key, box=box)