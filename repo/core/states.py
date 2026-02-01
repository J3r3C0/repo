import numpy as np
import hashlib

class State:
    def __init__(self, vector):
        self.vector = np.asarray(vector, dtype=float)
        self.weight = 1.0
        self.last_similarity = 1.0
        self.state_id = self._hash()

    def update(self, new_vec, sim, alpha=0.2):
        self.vector = (1 - alpha) * self.vector + alpha * new_vec
        self.weight += 0.1
        self.last_similarity = sim
        self.state_id = self._hash()

    def similarity(self, vec):
        num = np.dot(self.vector, vec)
        den = np.linalg.norm(self.vector) * np.linalg.norm(vec) + 1e-8
        return num / den

    def _hash(self):
        return hashlib.sha1(self.vector.tobytes()).hexdigest()
