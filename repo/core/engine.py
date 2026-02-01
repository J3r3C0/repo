import numpy as np
from .events import create_event_buffer
from .memory import Memory
from .observe import ResonanceLogger
from .cycle import run_cycle

class SheratanEngine:
    """
    Unified Engine for Phase 2.
    Orchestrates the deterministic resonance-memory cycle.
    """
    def __init__(self, config):
        self.config = config
        self.memory = Memory()
        log_path = getattr(config, "RESONANCE_LOG", "logs/resonance_log.csv")
        self.logger = ResonanceLogger(path=log_path)

        self.cycle_count = 0
        self.window_size = getattr(config, "WINDOW_SIZE", 1000)
        self.window_stride = getattr(config, "WINDOW_STRIDE", self.window_size)
        self.defaults = {
            "weight": getattr(config, "DEFAULT_WEIGHT", 1.0),
            "decay": getattr(config, "DEFAULT_DECAY", 0.95)
        }
        self.max_age = getattr(config, "MAX_SEGMENT_AGE", 100)
        self.max_active_states = getattr(config, "max_active_states", 1000)
        self._last_selected = set()

    def reset(self):
        """Resets the engine to the initial deterministic state."""
        self.cycle_count = 0
        self.memory.clear()
        self._last_selected = set()

    def process_events(self, raw_events):
        """
        Processes a batch of raw events through the resonance cycle.
        raw_events: list of tuples (id, value, timestamp, channel)
        """
        # 1. Create structured buffer (with rolling support)
        event_buffer = create_event_buffer(raw_events, self.window_size, self.window_stride)

        
        # 2. Run cycle (Resonance → Memory Update → Logging)
        resonances = run_cycle(
            event_buffer, 
            self.memory, 
            self.logger, 
            self.cycle_count, 
            self.defaults
        )
        
        # 3. Cleanup stale segments and enforce memory boundaries
        if self.cycle_count % 10 == 0:
            self.memory.cleanup_stale_segments(self.cycle_count, self.max_age)
            self.memory.enforce_boundaries(self.max_active_states)

        self.cycle_count += 1
        return resonances

    def replay_from_log(self, log_path):
        """
        Deterministic reconstruction of memory states from a resonance CSV.
        """
        import csv
        reconstructed_count = 0
        with open(log_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                cycle = int(row["cycle"])
                segment = int(row["segment"])
                resonance = float(row["resonance"])
                
                # Update memory without triggering a new log entry
                self.memory.update(segment, resonance, cycle, self.defaults)
                
                # Sync local cycle counter
                if cycle >= self.cycle_count:
                    self.cycle_count = cycle + 1
                reconstructed_count += 1
        return reconstructed_count

    def get_state_snapshot(self):
        """Returns current memory states."""
        return self.memory.snapshot()

    def shutdown(self):
        """Clean up resources."""
        self.logger.close()
