# RTX-960-safe defaults for Sheratan Resonance System

MAX_EVENTS = 1_000_000
DTYPE_FLOAT = "float32"
USE_STREAMS = False
ALLOW_ATOMICS = False

# Operational Modes: "analysis", "agent", "embedded"
SHERATAN_MODE = "analysis"

class SheratanConfig:
    def __init__(self):
        self.event_window = 512
        self.state_decay = 0.98
        self.resonance_threshold = 0.5
        self.max_active_states = 128
        self.identity_mode = "rule"
        self.top_k = 5

CONFIG = SheratanConfig()
