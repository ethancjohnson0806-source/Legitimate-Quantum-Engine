"""Solver Orchestrator — auto-picks best solver for a Hamiltonian.
"""
import numpy as np
from ..solvers.qite import QITE
from ..solvers.adapt_vqe import ADAPTVQE
from ..solvers.vqe_ground import spsa_vqe
from ..solvers.qng import QNGOptimizer

def auto_solve(H, n_qubits, target_precision=0.01, max_time_seconds=60):
    """
    Automatically select and run the best solver.

    Args:
        H: Hamiltonian matrix
        n_qubits: number of qubits
        target_precision: target energy error
        max_time_seconds: not enforced in this version

    Returns:
        dict with "energy", "solver_used", "parameters", "statevector"
    """
    # Heuristic selection
    is_local = _is_local_hamiltonian(H, n_qubits)

    if n_qubits <= 8:
        # Exact diagonalization
        eigs = np.linalg.eigh(H)
        return {
            "energy": float(eigs[0][0]),
            "statevector": eigs[1][:, 0],
            "solver_used": "exact_diagonalization",
            "parameters": None,
            "exact": True
        }

    if is_local and n_qubits <= 20:
        # Try QITE first (no ansatz needed)
        try:
            solver = QITE(n_qubits, H, dt=0.01, max_steps=300, verbose=False)
            result = solver.solve()
            return {
                "energy": result["energy"],
                "statevector": result["statevector"],
                "solver_used": "qite",
                "parameters": None,
                "steps": result["steps"],
                "exact": False
            }
        except Exception:
            pass

    if n_qubits <= 12:
        # ADAPT-VQE for medium size
        try:
            adapt = ADAPTVQE(n_qubits=n_qubits, hamiltonian=H, max_operators=6)
            result = adapt.solve(verbose=False)
            return {
                "energy": result["energy"],
                "parameters": result["parameters"],
                "solver_used": "adapt_vqe",
                "exact": False
            }
        except Exception:
            pass

    # Fallback: VQE + SPSA
    try:
        result = spsa_vqe(H, n_qubits, layers=2, max_iter=200, verbose=False)
        return {
            "energy": result["energy"],
            "parameters": result["parameters"],
            "solver_used": "vqe_spsa",
            "exact": False
        }
    except Exception as e:
        return {
            "energy": None,
            "error": str(e),
            "solver_used": "all_failed"
        }

def _is_local_hamiltonian(H, n):
    """Heuristic: check if H is sparse (suggesting local interactions)."""
    dim = H.shape[0]
    nnz = np.count_nonzero(np.abs(H) > 1e-10)
    sparsity = nnz / (dim * dim)
    # Local Hamiltonians are sparse
    return sparsity < 0.1
