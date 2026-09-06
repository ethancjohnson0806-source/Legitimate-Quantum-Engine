"""Legitimate Quantum Engine -- Core simulation backends."""
from .statevector import StatevectorSim
from .sparse_hamiltonian import SparseHamiltonian, build_sparse_heisenberg, sparse_lanczos
from .stabilizer import StabilizerSim
from .noise_models import apply_pauli_noise, depolarizing_channel
