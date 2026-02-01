import numpy as np
import hashlib

def encode_event(event, dim=16):
    h = hashlib.sha1(str(event.data).encode()).digest()
    vec = np.frombuffer(h, dtype=np.uint8)[:dim]
    vec = vec / 255.0
    return vec
