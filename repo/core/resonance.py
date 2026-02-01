from gpu.buffers import to_device, to_host
from gpu.primitives import segment_reduce_sum

def compute_resonance(similarity, state_weight, identity_factor):
    return similarity * state_weight * identity_factor

def compute_segment_resonance(event_buffer):
    """
    Computes aggregated resonance for each (channel, window) segment.
    event_buffer: structured numpy array (EVENT_DTYPE)
    returns: list of tuples (segment_id, resonance_value)
    """
    if len(event_buffer) == 0:
        return []
        
    d_segments = to_device(event_buffer["segment"])
    d_values   = to_device(event_buffer["value"])

    # Perform segment-based reduction
    segs, vals = segment_reduce_sum(d_segments, d_values)

    # Return results as list of host-side tuples
    return list(zip(
        to_host(segs).tolist(),
        to_host(vals).tolist()
    ))
