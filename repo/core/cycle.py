from core.resonance import compute_segment_resonance

def run_cycle(events, memory, logger, cycle, defaults):
    """
    Executes one Sheratan Resonance Cycle.
    1. Events → Resonance (GPU/CPU Primitives)
    2. Log Results (Observability)
    3. Update Memory (Deterministic State)
    """
    # 1. Compute segment-based resonance
    resonances = compute_segment_resonance(events)

    # 2. Log and update memory for each segment
    for segment, value in resonances:
        if logger:
            logger.log(cycle, segment, value)
        
        memory.update(segment, value, cycle, defaults)
    
    if logger:
        logger.flush()

    return resonances
