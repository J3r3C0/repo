import numpy as np

def select_top_states(
    memory_states, 
    threshold: float = 0.5, 
    top_k: int = 10, 
    channel_thresholds: dict = None,
    current_cycle: int = 0,
    persistence_window: int = 5,
    last_selected_segments: set = None
):
    """
    Phase 3/Gate B Identity Selection (Perception Kernel).
    
    1. Adaptive Thresholding: Determine effective threshold per channel.
    2. Persistence (Hysteresis): Keep segments that were recently selected even if below threshold.
    3. Selection: Filter by threshold OR persistence.
    4. Ranking: Value-weighted aging.
    """
    if not memory_states:
        return []

    if channel_thresholds is None:
        channel_thresholds = {}
    if last_selected_segments is None:
        last_selected_segments = set()

    candidates = []
    
    for s in memory_states:
        segment_id = int(s["segment"])
        channel = segment_id >> 32
        
        # Determine adaptive threshold
        # Base limit from config or channel override
        base_limit = channel_thresholds.get(channel, threshold)
        
        # Rule A: Threshold selection
        is_above_threshold = float(s["value"]) >= base_limit
        
        # Rule B: Persistence (Hysteresis)
        # If it was selected in the previous turn and is still "fresh", keep it.
        is_persistent = (segment_id in last_selected_segments) and \
                        ((current_cycle - int(s["last_seen"])) <= persistence_window)
        
        if is_above_threshold or is_persistent:
            candidates.append(s)

    # 4. Refined Ranking: (Value * DecayFactor) where DecayFactor decreases with age
    # We use a simple linear or exponential weight for last_seen.
    def ranking_score(state):
        val = float(state["value"])
        # Age penalty: reduce score by 1% for each cycle since last_seen
        age = current_cycle - int(state["last_seen"])
        age_penalty = max(0.0, 1.0 - (age * 0.01))
        return val * age_penalty

    candidates.sort(key=ranking_score, reverse=True)
    
    return candidates[:top_k]

def calculate_adaptive_threshold(memory_states, base_threshold: float, target_count: int = 20):
    """
    Refinement (Phase 3): Adjusts threshold based on 'load'.
    If too many segments are active, raise threshold to focus on high-resonance only.
    """
    if not memory_states:
        return base_threshold
        
    # Simple heuristic: if we have more resonance states than 2x target_count, 
    # increase threshold proportionally.
    count = len(memory_states)
    if count <= target_count:
        return base_threshold
        
    load_factor = count / target_count
    return base_threshold * min(2.0, load_factor)

def calculate_identity_score(state, current_cycle: int = 0):

    """
    Calculates a combined score for a segment state to determine its 
    significance beyond raw resonance, considering age.
    """
    val = float(state["value"])
    weight = float(state["weight"])
    age = current_cycle - int(state["last_seen"])
    age_weight = max(0.0, 1.0 - (age * 0.05)) # Stronger decay for scoring
    return val * weight * age_weight

