from dataclasses import dataclass

@dataclass
class SheratanConfig:
    event_window: int = 512
    state_decay: float = 0.02 # Slightly faster decay for dynamic research
    resonance_threshold: float = 0.6
    max_active_states: int = 128
    identity_mode: str = "rule"
    vector_dim: int = 16

CONFIG = SheratanConfig()
