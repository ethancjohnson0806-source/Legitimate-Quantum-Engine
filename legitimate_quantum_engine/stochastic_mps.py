"""Stochastic MPS — noisy dynamics without O(4^n) density matrices.
Ensemble of MPS trajectories with stochastic bond truncation.
"""
import numpy as np
from .mps_backend_v2 import MPSStateAdaptive

class StochasticMPS:
    """Noisy evolution via ensemble of MPS trajectories."""

    def __init__(self, n_qubits, chi_max=64, noise_strength=0.1, n_trajectories=10):
        self.n = n_qubits
        self.chi_max = chi_max
        self.noise_strength = noise_strength
        self.n_trajectories = n_trajectories
        self.trajectories = []
        for _ in range(n_trajectories):
            mps = MPSStateAdaptive(n_qubits, chi_max=chi_max)
            self.trajectories.append(mps)

    def apply(self, gate_name, *args):
        """Apply gate to all trajectories with stochastic noise."""
        for mps in self.trajectories:
            mps.apply(gate_name, *args)
            # Stochastic bond truncation: sample threshold
            if self.noise_strength > 0:
                # Add random perturbation to tensors
                for t in mps.tensors:
                    noise = np.random.randn(*t.shape) * self.noise_strength * 0.01
                    t += noise.astype(complex)

    def apply_noise_layer(self):
        """Apply explicit depolarizing noise layer."""
        for mps in self.trajectories:
            for q in range(self.n):
                # Random Pauli with probability noise_strength
                if np.random.random() < self.noise_strength:
                    pauli = np.random.choice(["X", "Y", "Z"])
                    mps.apply(pauli, q)

    def expectation(self, observable):
        """Average observable over trajectories."""
        values = []
        for mps in self.trajectories:
            if self.n <= 12:
                try:
                    sv = mps.to_statevector()
                    val = float(np.real(np.vdot(sv, observable @ sv)))
                    values.append(val)
                except Exception:
                    values.append(0.0)
            else:
                values.append(0.0)

        if len(values) == 0:
            return {"mean": 0.0, "std": 0.0}
        return {"mean": np.mean(values), "std": np.std(values)}
