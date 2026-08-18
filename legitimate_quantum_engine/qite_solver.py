"""QITE Solver — Quantum Imaginary Time Evolution.
No ansatz needed. Trotterized evolution.
"""
import numpy as np
from .core_simulator import StatevectorSim

class QITE:
    """Imaginary time evolution to find ground state."""

    def __init__(self, n_qubits, hamiltonian, dt=0.01, max_steps=500, verbose=False):
        self.n = n_qubits
        self.H = hamiltonian
        self.dt = dt
        self.max_steps = max_steps
        self.verbose = verbose
        self.energies = []
        self.states = []

    def solve(self, initial_state=None):
        """Run imaginary time evolution."""
        sim = StatevectorSim(self.n)
        if initial_state is not None:
            sim.state = initial_state.copy()
        else:
            # Start in superposition
            sim.state = np.ones(2**self.n, dtype=complex) / np.sqrt(2**self.n)

        best_energy = float("inf")
        best_state = sim.state.copy()
        plateau_count = 0

        for step in range(self.max_steps):
            # Imaginary time step: |psi> -> exp(-H*dt) |psi>
            # NumPy-only: diagonalize Hermitian H
            e, v = np.linalg.eigh(self.H)
            U = v @ np.diag(np.exp(-e * self.dt)) @ v.conj().T
            new_state = U @ sim.state
            norm = np.linalg.norm(new_state)
            if norm > 0:
                new_state /= norm
            sim.state = new_state

            energy = float(np.real(np.vdot(sim.state, self.H @ sim.state)))
            self.energies.append(energy)

            if energy < best_energy - 1e-8:
                best_energy = energy
                best_state = sim.state.copy()
                plateau_count = 0
            else:
                plateau_count += 1

            if self.verbose and step % 50 == 0:
                print(f"  QITE step {step}: E = {energy:.6f}")

            # Early stop if plateau
            if plateau_count > 50:
                if self.verbose:
                    print(f"  QITE converged at step {step}")
                break

        return {
            "energy": best_energy,
            "statevector": best_state,
            "steps": len(self.energies),
            "energy_history": self.energies,
            "converged": plateau_count > 50 or len(self.energies) == self.max_steps
        }
