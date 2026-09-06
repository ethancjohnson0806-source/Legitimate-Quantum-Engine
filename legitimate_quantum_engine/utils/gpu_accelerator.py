"""GPU accelerator stub -- Legitimate Quantum Engine v5.0"""
import numpy as np

class GPUQuantumSimulator:
    """Stub GPU simulator. Falls back to CPU."""
    def __init__(self, n_qubits):
        self.n = n_qubits
        self.state = np.zeros(2**n_qubits, dtype=complex)
        self.state[0] = 1.0
        self._has_gpu = False

    def apply(self, gate, *args):
        raise NotImplementedError("GPU not available. Use StatevectorSim instead.")

    def info(self):
        return {"gpu_available": False, "fallback": "CPU (StatevectorSim)"}
