"""
symmetry_solver.py — Legitimate Quantum Engine v4.0, Module 4

Symmetry-blocked exact diagonalization for spin-1/2 Hamiltonians.
Groups basis states by total S_z (magnetization), builds reduced
Hamiltonian blocks, and solves each sector independently.

Depends on: sparse_hamiltonian.py

Honest limitations:
    - Only S_z symmetry is implemented (particle-number / momentum TBD).
    - Hamiltonian must conserve S_z; results are approximate otherwise.
    - n_qubits <= 14 for phone comfort (16384 states per sector worst-case).
"""

import numpy as np
from math import comb
from ..core.sparse_hamiltonian import SparseHamiltonian, build_sparse_heisenberg


def compute_sz(basis_state: int, n_qubits: int) -> int:
    """
    Total S_z of a basis state in units of 1/2, multiplied by 2 so it is
    an integer:  sz = n_qubits - 2 * popcount(basis_state).

    Convention: |0> = spin up (+1/2), |1> = spin down (-1/2).
    """
    return n_qubits - 2 * bin(basis_state).count('1')


def build_sz_sectors(n_qubits: int):
    """
    Group basis states by S_z quantum number.

    Returns
    -------
    sectors : dict[int, list[int]]
        {sz_value: [basis_state, ...]} where sz_value = 2*S_z.
    """
    sectors = {}
    for b in range(1 << n_qubits):
        sz = compute_sz(b, n_qubits)
        sectors.setdefault(sz, []).append(b)
    return sectors


def build_sector_hamiltonian(H: SparseHamiltonian, sector_basis: list[int]):
    """
    Build the Hamiltonian restricted to a single S_z sector.

    Parameters
    ----------
    H : SparseHamiltonian
        Full Hamiltonian (must be finalized).
    sector_basis : list[int]
        Basis states in this sector.

    Returns
    -------
    H_sector : np.ndarray
        Dense matrix of shape (dim, dim), dtype=complex.
    """
    dim = len(sector_basis)
    H_sector = np.zeros((dim, dim), dtype=complex)

    idx_map = {b: i for i, b in enumerate(sector_basis)}

    for r, c, val in zip(H.rows, H.cols, H.data):
        i = idx_map.get(r)
        j = idx_map.get(c)
        if i is not None and j is not None:
            H_sector[i, j] += val

    return H_sector


def solve_symmetry_blocked(H: SparseHamiltonian):
    """
    Block-diagonalize H by S_z and solve each sector.

    Returns
    -------
    energy : float
        Global ground-state energy.
    psi : np.ndarray
        Ground-state vector in the full Hilbert space.
    sector_info : list[dict]
        Per-sector results for inspection.
    """
    if not H._finalized:
        raise RuntimeError("Call finalize() before solve_symmetry_blocked()")

    n = H.n
    sectors = build_sz_sectors(n)
    sector_info = []

    best_energy = float('inf')
    best_psi = None

    for sz, basis in sorted(sectors.items()):
        if len(basis) == 0:
            continue

        H_sec = build_sector_hamiltonian(H, basis)
        H_sec = (H_sec + H_sec.T.conj()) / 2

        eigs, vecs = np.linalg.eigh(H_sec)
        E0 = eigs[0]

        psi_full = np.zeros(H.N, dtype=complex)
        for i, b in enumerate(basis):
            psi_full[b] = vecs[i, 0]

        sector_info.append({
            'sz': sz,
            'dim': len(basis),
            'energy': E0,
            'psi': psi_full,
        })

        if E0 < best_energy:
            best_energy = E0
            best_psi = psi_full

    if best_psi is not None:
        best_psi /= np.linalg.norm(best_psi)

    return best_energy, best_psi, sector_info


# =============================================================================
# Tests
# =============================================================================

def test_sz_conservation():
    """S_z sectors partition the full Hilbert space."""
    print("\n=== Test: S_z Conservation ===")
    n = 4
    sectors = build_sz_sectors(n)
    total = sum(len(v) for v in sectors.values())
    assert total == 2 ** n, "Sectors must partition full Hilbert space"
    assert set(sectors.keys()) == {-4, -2, 0, 2, 4}
    print("  PASS")


def test_sector_dimensions():
    """Sector dimensions follow binomial coefficients."""
    print("\n=== Test: Sector Dimensions ===")
    n = 6
    sectors = build_sz_sectors(n)
    for sz, basis in sectors.items():
        k = (n - sz) // 2
        expected_dim = comb(n, k)
        assert len(basis) == expected_dim, f"Sector S_z={sz}: {len(basis)} != {expected_dim}"
    print("  PASS")


def test_heisenberg_symmetry():
    """Symmetry-blocked Heisenberg matches exact diagonalization."""
    print("\n=== Test: Heisenberg Symmetry Blocked ===")
    n = 8
    H = build_sparse_heisenberg(n, J=1.0, h=0.0)

    E_sym, psi_sym, info = solve_symmetry_blocked(H)

    H_dense = H.to_dense()
    eigs = np.linalg.eigvalsh(H_dense)
    E_exact = eigs[0]

    print(f"  Symmetry: {E_sym:.6f}, Exact: {E_exact:.6f}, diff: {abs(E_sym - E_exact):.2e}")
    assert abs(E_sym - E_exact) < 1e-10, f"Symmetry {E_sym} != exact {E_exact}"
    print("  PASS")


def test_magnetic_field_symmetry():
    """Z-field: ground state in maximal |S_z| sector."""
    print("\n=== Test: Magnetic Field Symmetry ===")
    n = 6
    H = build_sparse_heisenberg(n, J=0.0, h=2.0)
    E_sym, psi_sym, info = solve_symmetry_blocked(H)

    print(f"  Energy: {E_sym:.6f}, Expected: -6.0")
    assert abs(E_sym - (-6.0)) < 1e-10

    sz_values = [sec['sz'] for sec in info if abs(sec['energy'] - E_sym) < 1e-10]
    assert -n in sz_values, f"Ground state not in S_z=-n sector"
    print("  PASS")


def run_all_tests():
    print("=" * 60)
    print("SYMMETRY SOLVER TEST SUITE")
    print("=" * 60)
    test_sz_conservation()
    test_sector_dimensions()
    test_heisenberg_symmetry()
    test_magnetic_field_symmetry()
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
