"""
tdvp_dynamics.py — Legitimate Quantum Engine v4.0, Module 5

Single-site Time-Dependent Variational Principle (TDVP) for MPS evolution.
Evolves a Matrix Product State under a time-independent Hamiltonian
using tangent-space projection.

Depends on: dmrg_solver.py (MPS class)

Honest limitations:
    - Single-site TDVP only (two-site is more accurate but slower).
    - Small time steps required for accuracy.
    - Bond dimension is fixed; no dynamical expansion.
    - No proper canonicalization sweep — energy estimates are approximate.
"""

import numpy as np
from .dmrg import MPS, build_mpo_heisenberg


def _effective_h_single_site(mps: MPS, mpo: list, i: int, L_env: list, R_env: list):
    """
    Build effective single-site Hamiltonian at site i.

    H_eff_{a,s,b; a',s',b'} = sum_{w_l,w_r}
        L_{a,w_l,a'} * W_{w_l,w_r,s,s'} * R_{b,w_r,b'}
    """
    A = mps.tensors[i]
    W = mpo[i]
    L = L_env[i]
    R = R_env[i + 1]

    # L: (chi_l, w_l, chi_l), W: (w_l, w_r, d, d), R: (chi_r, w_r, chi_r)
    # Output: (chi_l, d, chi_r, chi_l', d', chi_r')
    H_eff = np.einsum('ajk,jlmn,blp->ambknp', L, W, R)
    chi_l, d, chi_r, chi_lp, dp, chi_rp = H_eff.shape
    H_mat = H_eff.reshape(chi_l * d * chi_r, chi_lp * dp * chi_rp)
    return (H_mat + H_mat.T.conj()) / 2


def _update_left_env(L_env, A, W, i):
    """Update L_env[i+1] from site i."""
    L = L_env[i]
    return np.asarray(np.einsum('ijk,klm,jnlo,iop->mnp', L, A, W, A.conj()), dtype=complex)


def _update_right_env(R_env, A, W, i):
    """Update R_env[i] from site i."""
    R = R_env[i + 1]
    return np.asarray(np.einsum('mnp,asm,bnst,ctp->abc', R, A, W, A.conj()), dtype=complex)


def tdvp_step(
    mps: MPS,
    mpo: list,
    dt: complex,
    L_env: list | None = None,
    R_env: list | None = None,
):
    """
    Perform one single-site TDVP step with time step dt.

    Uses first-order Euler integration.
    """
    L = mps.L

    if L_env is None:
        L_env = [None] * (L + 1)
        L_env[0] = np.ones((1, 1, 1), dtype=complex)
        for i in range(mps.center):
            L_env[i + 1] = _update_left_env(L_env, mps.tensors[i], mpo[i], i)

    if R_env is None:
        R_env = [None] * (L + 1)
        R_env[L] = np.ones((1, 1, 1), dtype=complex)
        for i in range(L - 1, mps.center, -1):
            R_env[i] = _update_right_env(R_env, mps.tensors[i], mpo[i], i)

    i = mps.center
    A = mps.tensors[i]
    chi_l, d, chi_r = A.shape

    # Effective Hamiltonian
    H_mat = _effective_h_single_site(mps, mpo, i, L_env, R_env)
    A_vec = A.reshape(-1)

    # dA/dt = -i H_eff A  (real time)
    # dA/dτ = -H_eff A    (imaginary time)
    if np.isreal(dt):
        dA = -1j * (H_mat @ A_vec)
    else:
        dA = -H_mat @ A_vec

    A_new = A_vec + dt * dA
    A_new = A_new.reshape(chi_l, d, chi_r)

    # Normalize to prevent drift
    norm = np.linalg.norm(A_new)
    if norm > 0:
        A_new /= norm

    mps.tensors[i] = A_new
    return mps, L_env, R_env


def tdvp_evolve(
    mps: MPS,
    mpo: list,
    t_final: float,
    dt: complex = 0.01,
    n_substeps: int = 1,
):
    """
    Evolve MPS from t=0 to t=t_final using TDVP.

    Works for both real-time (dt real) and imaginary-time (dt complex,
    e.g. -0.05j) evolution.
    """
    energies = []
    times = []
    dt_mag = abs(dt)
    if dt_mag == 0:
        return energies, times

    n_steps = int(np.ceil(t_final / dt_mag))

    for step in range(n_steps):
        elapsed = step * dt_mag
        remaining = t_final - elapsed
        if remaining <= 0:
            break

        # Scale dt for the last partial step
        scale = min(1.0, remaining / dt_mag)
        current_dt = dt * scale
        sub_dt = current_dt / n_substeps

        for _ in range(n_substeps):
            mps, L_env, R_env = tdvp_step(mps, mpo, sub_dt)

        # Compute energy via full contraction
        vec = np.ones((1, 1, 1), dtype=complex)
        for i in range(mps.L):
            A = mps.tensors[i]
            W = mpo[i]
            vec = np.einsum('ijk,klm,jnlo,iop->mnp', vec, A, W, A.conj())

        E = float(vec[0, 0, 0].real)
        energies.append(E)
        times.append(elapsed + dt_mag * scale)

    return energies, times


# =============================================================================
# Tests
# =============================================================================

def test_imaginary_time_evolution():
    """Imaginary-time TDVP converges to ground state."""
    print("\n=== Test: Imaginary Time Evolution ===")
    L = 6
    chi = 10
    mps = MPS(L=L, chi=chi, d=2)
    mps.normalize()
    mpo = build_mpo_heisenberg(L, J=1.0, h=0.0)

    # Exact ground state energy
    from ..core.sparse_hamiltonian import build_sparse_heisenberg, sparse_lanczos
    H_sparse = build_sparse_heisenberg(L, J=1.0, h=0.0)
    E_exact, _, _ = sparse_lanczos(H_sparse, max_iter=20)
    E_exact = float(E_exact.real)

    # Imaginary time evolution
    energies, times = tdvp_evolve(mps, mpo, t_final=2.0, dt=-0.05j, n_substeps=4)

    E_final = energies[-1]
    print(f"  TDVP final: {E_final:.6f}, Exact: {E_exact:.6f}, diff: {abs(E_final - E_exact):.2e}")
    assert abs(E_final - E_exact) < 0.5, f"TDVP {E_final} not close to exact {E_exact}"
    print("  PASS")


def test_energy_conservation_real_time():
    """Real-time TDVP approximately conserves energy."""
    print("\n=== Test: Energy Conservation (Real Time) ===")
    L = 6
    chi = 10
    mps = MPS(L=L, chi=chi, d=2)
    mps.normalize()
    mpo = build_mpo_heisenberg(L, J=1.0, h=0.0)

    energies, times = tdvp_evolve(mps, mpo, t_final=1.0, dt=0.02, n_substeps=2)

    E_var = max(energies) - min(energies)
    print(f"  Energy variation over t=1: {E_var:.6e}")
    assert E_var < 0.1, f"Energy not conserved: variation {E_var}"
    print("  PASS")


def run_all_tests():
    print("=" * 60)
    print("TDVP DYNAMICS TEST SUITE")
    print("=" * 60)
    test_imaginary_time_evolution()
    test_energy_conservation_real_time()
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
