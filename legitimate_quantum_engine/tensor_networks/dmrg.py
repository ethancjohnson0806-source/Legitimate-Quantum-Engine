"""
dmrg_solver.py — Legitimate Quantum Engine v4.0, Module 2

Density Matrix Renormalization Group (DMRG) for 1D ground states.
Pure NumPy. Two-site algorithm with dense eigensolver.

Honest limitation: bond dimension χ should be <= 30 for phone comfort
(10000 x 10000 dense matrix at χ=50 is ~800MB). For larger χ, use single-site
or external sparse eigensolvers.
"""

import numpy as np


# =============================================================================
# Minimal MPS (to be replaced by MPS v2 in production)
# =============================================================================

class MPS:
    """Minimal Matrix Product State for spin-1/2 systems."""

    def __init__(self, L: int, chi: int, d: int = 2):
        self.L = L
        self.chi = chi
        self.d = d
        # Tensors: list of (chi_left, d, chi_right)
        # Boundary conditions: chi_0 = chi_L = 1
        self.tensors = []
        for i in range(L):
            chi_l = 1 if i == 0 else chi
            chi_r = 1 if i == L - 1 else chi
            self.tensors.append(
                np.random.randn(chi_l, d, chi_r) + 1j * np.random.randn(chi_l, d, chi_r)
            )
        self.center = 0  # orthogonality center

    def normalize(self):
        """Normalize the MPS to total norm 1."""
        vec = np.ones((1, 1), dtype=complex)
        for i in range(self.L):
            A = self.tensors[i]
            # Correct contraction: bra and ket right bonds are independent
            vec = np.einsum('ab,bsc,asd->cd', vec, A, A.conj())
        norm = np.sqrt(np.abs(vec[0, 0]))
        if norm > 0:
            self.tensors[0] /= norm

    def move_center(self, target: int):
        """Move orthogonality center to target site via SVD sweeps."""
        while self.center < target:
            self._shift_center_right()
        while self.center > target:
            self._shift_center_left()

    def _shift_center_right(self):
        """SVD at center, push singular values right."""
        i = self.center
        A = self.tensors[i]  # (chi_l, d, chi_r)
        chi_l, d, chi_r = A.shape
        mat = A.reshape(chi_l * d, chi_r)
        U, s, Vh = np.linalg.svd(mat, full_matrices=False)
        # Truncate
        chi_new = min(self.chi, len(s))
        U = U[:, :chi_new]
        s = s[:chi_new]
        Vh = Vh[:chi_new, :]
        # Left-normalized tensor
        self.tensors[i] = U.reshape(chi_l, d, chi_new)
        # Absorb singular values into next tensor
        SV = np.diag(s) @ Vh  # (chi_new, chi_r)
        self.tensors[i + 1] = np.einsum('ab,bsc->asc', SV, self.tensors[i + 1])
        self.center += 1

    def _shift_center_left(self):
        """SVD at center, push singular values left."""
        i = self.center
        A = self.tensors[i]  # (chi_l, d, chi_r)
        chi_l, d, chi_r = A.shape
        mat = A.reshape(chi_l, d * chi_r)
        U, s, Vh = np.linalg.svd(mat, full_matrices=False)
        chi_new = min(self.chi, len(s))
        U = U[:, :chi_new]
        s = s[:chi_new]
        Vh = Vh[:chi_new, :]
        # Right-normalized tensor
        self.tensors[i] = Vh.reshape(chi_new, d, chi_r)
        # Absorb singular values into previous tensor
        US = U @ np.diag(s)  # (chi_l, chi_new)
        self.tensors[i - 1] = np.einsum('asc,cb->asb', self.tensors[i - 1], US)
        self.center -= 1

    def two_site_tensor(self, i: int):
        """Combine tensors at sites i and i+1 into two-site tensor."""
        # theta = A_i @ A_{i+1}
        return np.einsum('asb,btc->astc', self.tensors[i], self.tensors[i + 1])

    def set_two_site(self, i: int, theta: np.ndarray, direction: str = 'right'):
        """Split two-site tensor and update MPS."""
        chi_l, d1, d2, chi_r = theta.shape
        mat = theta.reshape(chi_l * d1, d2 * chi_r)
        U, s, Vh = np.linalg.svd(mat, full_matrices=False)
        chi_new = min(self.chi, len(s))
        U = U[:, :chi_new]
        s = s[:chi_new]
        Vh = Vh[:chi_new, :]

        if direction == 'right':
            self.tensors[i] = U.reshape(chi_l, d1, chi_new)
            SV = np.diag(s) @ Vh
            self.tensors[i + 1] = SV.reshape(chi_new, d2, chi_r)
            self.center = i + 1
        else:
            self.tensors[i] = (U @ np.diag(s)).reshape(chi_l, d1, chi_new)
            self.tensors[i + 1] = Vh.reshape(chi_new, d2, chi_r)
            self.center = i


# =============================================================================
# MPO Builder
# =============================================================================

def build_mpo_heisenberg(L: int, J: float = 1.0, h: float = 0.0):
    """
    Build MPO for 1D Heisenberg model:
        H = J * sum_i (S_i^x S_{i+1}^x + S_i^y S_{i+1}^y + S_i^z S_{i+1}^z)
          + h * sum_i S_i^z

    Returns list of L tensors, each of shape (W_left, W_right, d, d) where W=5.
    """
    d = 2
    sx = np.array([[0, 1], [1, 0]], dtype=complex) / 2
    sy = np.array([[0, -1j], [1j, 0]], dtype=complex) / 2
    sz = np.array([[1, 0], [0, -1]], dtype=complex) / 2
    I = np.eye(2, dtype=complex)
    Z = np.zeros((2, 2), dtype=complex)

    # MPO matrix as a 5x5 grid of operators — built directly as complex arrays
    # Avoid dtype=object; always use concrete complex arrays.
    W = [
        [I,    Z,    Z,    Z,    Z],
        [J*sx, Z,    Z,    Z,    Z],
        [J*sy, Z,    Z,    Z,    Z],
        [J*sz, Z,    Z,    Z,    Z],
        [h*sz, sx,   sy,   sz,   I],
    ]

    mpo = []
    for i in range(L):
        if i == 0:
            # First site: last row only -> shape (1, 5, d, d)
            tensor = np.stack([W[4][j] for j in range(5)], axis=0)  # (5, d, d)
            tensor = tensor[np.newaxis, :, :, :]  # (1, 5, d, d)
        elif i == L - 1:
            # Last site: first column only -> shape (5, 1, d, d)
            tensor = np.stack([W[j][0] for j in range(5)], axis=0)  # (5, d, d)
            tensor = tensor[:, np.newaxis, :, :]  # (5, 1, d, d)
        else:
            # Bulk: full 5x5 -> shape (5, 5, d, d)
            tensor = np.zeros((5, 5, d, d), dtype=complex)
            for a in range(5):
                for b in range(5):
                    tensor[a, b, :, :] = W[a][b]
        mpo.append(tensor)
    return mpo


# =============================================================================
# DMRG Solver
# =============================================================================

class DMRG:
    """
    Two-site DMRG solver.

    Parameters:
        mps     : MPS object
        mpo     : list of MPO tensors
        chi     : maximum bond dimension
        n_sweeps: number of sweeps
        tol     : energy convergence tolerance
    """

    def __init__(self, mps: MPS, mpo: list, chi: int = 20, n_sweeps: int = 10, tol: float = 1e-8):
        self.mps = mps
        self.mpo = mpo
        self.chi = chi
        self.n_sweeps = n_sweeps
        self.tol = tol
        self.energies = []
        self._build_environments()

    def _build_environments(self):
        """Initialize left and right environments."""
        L = self.mps.L
        d = self.mps.d
        # Left environments: L[i] is environment to the left of site i
        self.L_env = [None] * (L + 1)
        self.L_env[0] = np.ones((1, 1, 1), dtype=complex)  # (chi_mps, chi_mpo, chi_mps)
        # Right environments: R[i] is environment to the right of site i
        self.R_env = [None] * (L + 1)
        self.R_env[L] = np.ones((1, 1, 1), dtype=complex)

        # Initialize right environments by contracting from right
        for i in range(L - 1, 0, -1):
            self._update_right_env(i)

    def _update_left_env(self, i: int):
        """Update L_env[i+1] using tensor at site i."""
        A = self.mps.tensors[i]  # (chi_l, d, chi_r)
        W = self.mpo[i]  # (w_l, w_r, d, d)
        L = self.L_env[i]  # (chi_l, w_l, chi_l)
        # L[i+1]_{c, w_r, c'} = sum_{a, w_l, b, s, t} L_{a, w_l, b} * A_{b, s, c} * W_{w_l, w_r, s, t} * conj(A)_{a, t, c'}
        self.L_env[i + 1] = np.asarray(np.einsum('ijk,klm,jnlo,iop->mnp', L, A, W, A.conj()), dtype=complex)

    def _update_right_env(self, i: int):
        """Update R_env[i] using tensor at site i."""
        A = self.mps.tensors[i]  # (chi_l, d, chi_r)
        W = self.mpo[i]  # (w_l, w_r, d, d)
        R = self.R_env[i + 1]  # (chi_r, w_r, chi_r)
        # R[i]_{a, w_l, a'} = sum_{c, w_r, s, t, c'} R_{c, w_r, c'} * A_{a, s, c} * W_{w_l, w_r, s, t} * conj(A)_{a', t, c'}
        self.R_env[i] = np.asarray(np.einsum('mnp,asm,bnst,ctp->abc', R, A, W, A.conj()), dtype=complex)

    def solve(self):
        """Run DMRG sweeps until convergence or max sweeps."""
        steps_per_sweep = 2 * (self.mps.L - 1)
        for sweep in range(self.n_sweeps):
            # Right sweep
            for i in range(self.mps.L - 1):
                energy = self._optimize_two_site(i, direction='right')
                self.energies.append(energy)
                self._update_left_env(i)

            # Left sweep
            for i in range(self.mps.L - 2, -1, -1):
                energy = self._optimize_two_site(i, direction='left')
                self.energies.append(energy)
                self._update_right_env(i + 1)

            # Check convergence over the last full sweep
            if len(self.energies) >= steps_per_sweep:
                recent = self.energies[-steps_per_sweep:]
                if max(recent) - min(recent) < self.tol:
                    print(f"  Converged at sweep {sweep}")
                    break

        # Return the best energy from the last sweep, not the last step
        if len(self.energies) >= steps_per_sweep:
            return min(self.energies[-steps_per_sweep:])
        return min(self.energies)

    def _optimize_two_site(self, i: int, direction: str = 'right'):
        """
        Optimize the two-site wavefunction at sites (i, i+1).
        Forms effective Hamiltonian and finds ground state via dense eigensolver.
        """
        # Two-site tensor
        theta = self.mps.two_site_tensor(i)  # (chi_l, d, d, chi_r)
        chi_l, d1, d2, chi_r = theta.shape

        # Effective Hamiltonian
        L = self.L_env[i]  # (chi_l, w_l, chi_l)
        W1 = self.mpo[i]  # (w_l, w_m, d1, d1)
        W2 = self.mpo[i + 1]  # (w_m, w_r, d2, d2)
        R = self.R_env[i + 2]  # (chi_r, w_r, chi_r)

        # H_eff_{a,s1,s2,c; a',s1',s2',c'} = sum_{w_l,w_m,w_r}
        #   L_{a,w_l,a'} * W1_{w_l,w_m,s1,s1'} * W2_{w_m,w_r,s2,s2'} * R_{c,w_r,c'}
        H_eff = np.asarray(np.einsum('ijk,jlmn,lopq,ros->imprknqs', L, W1, W2, R), dtype=complex)

        # Reshape to matrix
        dim = chi_l * d1 * d2 * chi_r
        H_mat = H_eff.reshape(dim, dim)

        # Ensure Hermitian
        H_mat = (H_mat + H_mat.T.conj()) / 2

        # Dense eigensolver (smallest eigenvalue)
        # For dim > 5000, this is slow. For phone use, keep chi <= 30.
        if dim > 8000:
            print(f"  Warning: H_eff dimension {dim} is large. Consider reducing chi.")

        eigs, vecs = np.linalg.eigh(H_mat)
        ground_energy = eigs[0]
        ground_state = vecs[:, 0]

        # Reshape back to two-site tensor
        theta_opt = ground_state.reshape(chi_l, d1, d2, chi_r)

        # Split and update MPS
        self.mps.set_two_site(i, theta_opt, direction=direction)

        return ground_energy.real

    def correlation_length(self):
        """Estimate correlation length from transfer matrix."""
        # Build transfer matrix T = sum_s A[s] \otimes conj(A[s])
        # For simplicity, use the center tensor
        A = self.mps.tensors[self.mps.center]
        chi_l, d, chi_r = A.shape
        T = np.einsum('asc,bsc->ab', A, A.conj())  # (chi_l, chi_l)
        eigs = np.linalg.eigvals(T)
        eigs = np.sort(np.abs(eigs))[::-1]
        if len(eigs) > 1 and eigs[1] > 1e-10:
            return -1.0 / np.log(eigs[1] / eigs[0])
        return float('inf')


# =============================================================================
# Tests
# =============================================================================

def test_heisenberg_ground_state():
    """DMRG on 10-site Heisenberg chain, compare to exact (Bethe ansatz ~ -4.258)."""
    print("\n=== Test: Heisenberg Ground State ===")
    L = 10
    chi = 20
    mps = MPS(L=L, chi=chi, d=2)
    mps.normalize()
    mpo = build_mpo_heisenberg(L, J=1.0, h=0.0)

    dmrg = DMRG(mps, mpo, chi=chi, n_sweeps=6, tol=1e-8)
    energy = dmrg.solve()

    # Exact ground state energy for L=10 Heisenberg (open boundary) from Bethe ansatz
    # Approximate: E_0 ≈ -4.258 for L=10
    print(f"  DMRG energy: {energy:.6f}")
    print(f"  Exact (approx): -4.258")
    assert energy < -3.5, f"Energy {energy} too high"
    print("  PASS")


def test_magnetic_field():
    """DMRG with magnetic field: all spins align."""
    print("\n=== Test: Magnetic Field ===")
    L = 8
    chi = 10
    mps = MPS(L=L, chi=chi, d=2)
    mps.normalize()
    mpo = build_mpo_heisenberg(L, J=0.0, h=2.0)  # Only field term

    dmrg = DMRG(mps, mpo, chi=chi, n_sweeps=4, tol=1e-8)
    energy = dmrg.solve()

    # Ground state: all spins down, energy = -h * L/2 = -2 * 8 * 0.5 = -8
    # Wait: S^z eigenvalues are +/- 1/2, so for spin-1/2, h * sum S^z
    # All down: sum S^z = -L/2 = -4, energy = h * (-4) = -8
    print(f"  DMRG energy: {energy:.6f}")
    print(f"  Expected: -8.0")
    assert abs(energy - (-8.0)) < 0.1, f"Energy {energy} not close to -8"
    print("  PASS")


def test_bond_dimension_scaling():
    """Energy improves with larger bond dimension."""
    print("\n=== Test: Bond Dimension Scaling ===")
    L = 12
    energies = []
    for chi in [5, 10, 20]:
        mps = MPS(L=L, chi=chi, d=2)
        mps.normalize()
        mpo = build_mpo_heisenberg(L, J=1.0, h=0.0)
        dmrg = DMRG(mps, mpo, chi=chi, n_sweeps=6, tol=1e-6)
        e = dmrg.solve()
        energies.append(e)
        print(f"  chi={chi}: E={e:.6f}")

    assert energies[1] < energies[0], "Energy should improve with chi"
    assert energies[2] < energies[1], "Energy should improve with chi"
    print("  PASS")


def test_correlation_length():
    """Correlation length is finite for gapped system."""
    print("\n=== Test: Correlation Length ===")
    L = 12
    chi = 10
    mps = MPS(L=L, chi=chi, d=2)
    mps.normalize()
    mpo = build_mpo_heisenberg(L, J=1.0, h=0.0)
    dmrg = DMRG(mps, mpo, chi=chi, n_sweeps=4, tol=1e-6)
    dmrg.solve()
    xi = dmrg.correlation_length()
    print(f"  Correlation length: {xi:.2f} sites")
    assert xi > 0 and xi < L, f"Correlation length {xi} out of range"
    print("  PASS")


def run_all_tests():
    print("=" * 60)
    print("DMRG SOLVER TEST SUITE")
    print("=" * 60)
    test_heisenberg_ground_state()
    test_magnetic_field()
    test_bond_dimension_scaling()
    test_correlation_length()
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
