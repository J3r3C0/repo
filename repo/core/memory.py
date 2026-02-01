import numpy as np

# Sheratan Phase 2: Memory State Format
STATE_DTYPE = np.dtype([
    ("segment", np.uint64),
    ("value", np.float32),
    ("weight", np.float32),
    ("decay", np.float32),
    ("last_seen", np.uint32),
])

class Memory:
    """
    Deterministic memory system.
    Manages states indexed by segment_id.
    """
    def __init__(self):
        self.states = {} # segment_id -> structured_array (single element)

    def clear(self):
        """Clears all memory states."""
        self.states = {}

    def update(self, segment: int, resonance: float, cycle: int, defaults: dict):
        """
        Updates memory state for a given segment based on resonance.
        Rule 1: Activation (state.value += resonance * weight)
        Rule 2: Decay (state.value *= decay)
        """
        if segment not in self.states:
            # Initialize new state
            self.states[segment] = np.zeros(1, dtype=STATE_DTYPE)[0]
            self.states[segment]["segment"] = segment
            self.states[segment]["weight"] = defaults.get("weight", 1.0)
            self.states[segment]["decay"] = defaults.get("decay", 0.95)

        state = self.states[segment]
        # 1. Activate
        state["value"] += np.float32(resonance) * state["weight"]
        # 2. Apply Decay (Deterministic aging)
        state["value"] *= state["decay"]
        # 3. Mark last seen cycle
        state["last_seen"] = np.uint32(cycle)

    def snapshot(self):
        """Returns all current memory states."""
        return list(self.states.values())

    def get_state(self, segment: int):
        """Returns the state for a specific segment if it exists."""
        return self.states.get(segment)

    def cleanup_stale_segments(self, current_cycle: int, max_age: int):
        """
        Removes segments that have not been seen for more than max_age cycles.
        Ensures memory remains bounded and deterministic.
        """
        stale_keys = [
            seg for seg, state in self.states.items()
            if (current_cycle - int(state["last_seen"])) > max_age
        ]
        for k in stale_keys:
            del self.states[k]
        return len(stale_keys)

    def enforce_boundaries(self, max_active_states: int):
        """
        Ensures the total number of segments in memory does not exceed max_active_states.
        Prunes segments with the lowest resonance values (least significant).
        """
        if len(self.states) <= max_active_states:
            return 0
        
        # Sort current states by resonance value ascending (lowest first)
        # Using a list of tuples (segment_id, value)
        sorted_states = sorted(
            self.states.items(), 
            key=lambda item: (float(item[1]["value"]), int(item[1]["last_seen"]))
        )
        
        num_to_remove = len(self.states) - max_active_states
        to_prune = sorted_states[:num_to_remove]
        
        for k, _ in to_prune:
            del self.states[k]
            
        return num_to_remove
    def get_state_hash(self):
        """
        Computes a deterministic hash of the entire memory state.
        Uses SHA256 over the bytes of all current states sorted by segment ID.
        """
        import hashlib
        sorted_keys = sorted(self.states.keys())
        hasher = hashlib.sha256()
        for k in sorted_keys:
            hasher.update(self.states[k].tobytes())
        return hasher.hexdigest()
