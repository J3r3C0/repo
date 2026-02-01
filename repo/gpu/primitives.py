import numpy as np

try:
    import cupy as cp
    HAS_GPU = True
except ImportError:
    HAS_GPU = False

def reduce_values(device_array, op="sum"):
    """
    Reduces values in the device array using the specified operation.
    """
    if not HAS_GPU:
        if op == "sum": return np.sum(device_array)
        return device_array
    
    if op == "sum": return cp.sum(device_array)
    return device_array

def segment_reduce_sum(segments, values):
    """
    segments: uint64 array (device or host)
    values: float32 array (device or host)
    returns: (unique_segments, reduced_values)
    """
    if not HAS_GPU:
        # CPU Fallback using numpy
        unique_segs = np.unique(segments)
        reduced_vals = []
        for seg in unique_segs:
            reduced_vals.append(np.sum(values[segments == seg]))
        return unique_segs, np.array(reduced_vals, dtype=np.float32)

    # GPU Implementation (Optimized via Prefix Scan)
    # 1. Radix Sort
    idx = cp.argsort(segments)
    sorted_segs = segments[idx]
    sorted_vals = values[idx]

    # 2. Identify Segment Boundaries
    # mask[i] is True if sorted_segs[i] starts a new segment
    mask = cp.zeros(len(sorted_segs), dtype=bool)
    mask[0] = True
    mask[1:] = sorted_segs[1:] != sorted_segs[:-1]
    
    unique_segs = sorted_segs[mask]
    
    # 3. Compute Prefix Sum (Scan)
    sums = cp.cumsum(sorted_vals)
    
    # 4. Extract Segment Totals
    # Find indices where segments end
    end_indices = cp.where(mask)[0]
    # Shift to get the end of each unique segment
    end_indices = cp.concatenate([end_indices[1:], cp.array([len(sorted_segs)])])
    
    # total[i] = sums[end_indices[i]-1] - sums[end_indices[i-1]-1]
    segment_sums = sums[end_indices - 1]
    # Subtract previous segment's end sum to get current segment total
    reduced_vals = cp.zeros(len(unique_segs), dtype=cp.float32)
    reduced_vals[0] = segment_sums[0]
    reduced_vals[1:] = segment_sums[1:] - segment_sums[:-1]

    return unique_segs, reduced_vals

def prefix_scan(device_array, op="sum"):
    """
    Performs a prefix scan on the device array.
    """
    if not HAS_GPU:
        return np.cumsum(device_array)
    return cp.cumsum(device_array)
