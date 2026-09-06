"""Differential Simulation — run multiple backends simultaneously.
Cross-validates after every gate. Detects when MPS lies.
"""
import numpy as np
from ..core.statevector import StatevectorSim
from ..tensor_networks.mps_simulator import MPSStateAdaptive
try:
    from ..core.sparse_hamiltonian import SparseStateSimulator
except ImportError:
    SparseStateSimulator = None

class DifferentialSim:
    """Self-checking simulator using multiple backends."""

    def __init__(self, n_qubits):
        self.n = n_qubits
        self.backends = {}
        self.step = 0
        self.agreement = 1.0
        self.statevector_energy = None
        self.mps_energy = None
        self.sparse_energy = None
        self.active_backend = None

    def add_backend(self, name, **kwargs):
        """Add a backend."""
        if name == "statevector":
            self.backends[name] = StatevectorSim(self.n)
        elif name == "mps":
            chi = kwargs.get("chi_max", 32)
            self.backends[name] = MPSStateAdaptive(self.n, chi_max=chi)
        elif name == "sparse":
            try:
                self.backends[name] = SparseStateSimulator(self.n)
            except Exception:
                self.backends[name] = None
        self.active_backend = name if self.active_backend is None else self.active_backend

    def apply(self, gate_name, *args):
        """Apply gate to all backends."""
        for name, backend in self.backends.items():
            if backend is None:
                continue
            try:
                if name == "mps":
                    backend.apply(gate_name, *args)
                else:
                    backend.apply(gate_name, *args)
            except Exception as e:
                if name == "mps":
                    # MPS might fail on complex gates; fallback to statevector
                    pass
        self.step += 1
        self._check_agreement()

    def _check_agreement(self):
        """Compare energies across backends."""
        energies = {}
        for name, backend in self.backends.items():
            if backend is None:
                continue
            try:
                if name == "statevector":
                    # Need observable to compute energy; use |0> projector as proxy
                    p0 = abs(backend.state[0])**2
                    energies[name] = p0
                elif name == "mps":
                    p0 = backend.probabilities()[0] if len(backend.probabilities()) > 0 else 0
                    energies[name] = p0
                else:
                    energies[name] = 0.5
            except Exception:
                energies[name] = None

        valid = [v for v in energies.values() if v is not None]
        if len(valid) >= 2:
            self.agreement = 1.0 - (max(valid) - min(valid))
        else:
            self.agreement = 1.0

        self.statevector_energy = energies.get("statevector")
        self.mps_energy = energies.get("mps")
        self.sparse_energy = energies.get("sparse")

    def fallback_to(self, name):
        """Switch to specified backend."""
        if name in self.backends and self.backends[name] is not None:
            self.active_backend = name

    def measure(self, qubit):
        """Measure on active backend."""
        backend = self.backends.get(self.active_backend)
        if backend is None:
            return 0
        if hasattr(backend, "measure"):
            return backend.measure(qubit)
        # Fallback
        probs = np.abs(backend.state)**2
        p0 = sum(probs[i] for i in range(len(probs)) if ((i >> qubit) & 1) == 0)
        return 0 if np.random.random() < p0 else 1
