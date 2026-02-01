import numpy as np

try:
    import cupy as cp
    HAS_GPU = True
except ImportError:
    HAS_GPU = False

def to_device(np_array: np.ndarray):
    """
    Transfers a NumPy array to the GPU (as a Cupy array).
    """
    if not HAS_GPU:
        return np_array
    return cp.asarray(np_array)

def to_host(device_array):
    """
    Transfers a GPU array back to the CPU (NumPy).
    """
    if not HAS_GPU:
        return device_array
    try:
        import cupy as cp
        return cp.asnumpy(device_array)
    except (ImportError, TypeError):
        return device_array
