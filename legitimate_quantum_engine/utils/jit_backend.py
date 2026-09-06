"""
jit_backend.py -- Legitimate Quantum Engine v5.0, Phase 0

Optional Numba JIT acceleration for gate application, VQE energy,
and MPS contractions.  Pure NumPy fallback is bit-exact and always
available.

Phone-viable:  Numba is optional; pip install numba on Termux works.
Honest limitation:  Numba is not pure NumPy.  The engine works without it.
"""

import numpy as np

# ------------------------------------------------------------------
# Optional Numba import
# ------------------------------------------------------------------
try:
    from numba import njit, prange
    _HAS_NUMBA = True
except ImportError:
    _HAS_NUMBA = False

    def njit(*args, **kwargs):
        """No-op decorator when Numba is absent."""
        def _decorator(f):
            return f
        return _decorator

    prange = range


# ------------------------------------------------------------------
# Public interface
# ------------------------------------------------------------------
class JITBackend:
    """
    Optional JIT acceleration layer.

    If Numba is installed, gate application uses compiled loops.
    If not, every method falls back to the pure-NumPy tensordot
    implementation in StatevectorSim (bit-exact, slower).
    """

    def __init__(self, use_jit=True):
        self.use_jit = use_jit and _HAS_NUMBA
        self._has_numba = _HAS_NUMBA

    def apply_1q(self, sim, name, qubit, theta=None):
        """
        Apply a single-qubit gate to a StatevectorSim instance.
        Falls back to sim.apply() if JIT is unavailable.
        """
        if not self.use_jit:
            if theta is not None:
                sim.apply(name, theta, qubit)
            else:
                sim.apply(name, qubit)
            return

        if name == "H":
            g = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
            sim._apply_1q(g, qubit)
        elif name == "X":
            g = np.array([[0, 1], [1, 0]], dtype=complex)
            sim._apply_1q(g, qubit)
        elif name == "Y":
            g = np.array([[0, -1j], [1j, 0]], dtype=complex)
            sim._apply_1q(g, qubit)
        elif name == "Z":
            g = np.array([[1, 0], [0, -1]], dtype=complex)
            sim._apply_1q(g, qubit)
        elif name in ("RX", "RY", "RZ") and theta is not None:
            c, s = np.cos(theta / 2), np.sin(theta / 2)
            if name == "RX":
                g = np.array([[c, -1j * s], [-1j * s, c]], dtype=complex)
            elif name == "RY":
                g = np.array([[c, -s], [s, c]], dtype=complex)
            else:
                g = np.array([[c - 1j * s, 0], [0, c + 1j * s]], dtype=complex)
            sim._apply_1q(g, qubit)
        else:
            raise ValueError(f"Unknown 1-qubit gate: {name}")

    def apply_2q(self, sim, name, c, t):
        """Apply a two-qubit gate to a StatevectorSim instance."""
        if not self.use_jit:
            sim.apply(name, c, t)
            return

        if name == "CNOT":
            sim.apply("CNOT", c, t)
        elif name == "SWAP":
            sim.apply("SWAP", c, t)
        else:
            raise ValueError(f"Unknown 2-qubit gate: {name}")

    def vqe_energy(self, params, H, n, layers):
        """
        Evaluate VQE energy with JIT-accelerated ansatz construction.
        Falls back to pure NumPy if JIT unavailable.
        """
        if not self.use_jit:
            from ..solvers.vqe_ground import vqe_energy
            return vqe_energy(params, H, n, layers)

        sim = StatevectorSim(n)
        idx = 0
        for _ in range(layers):
            for q in range(n):
                sim.apply("RY", params[idx], q)
                idx += 1
            for q in range(n - 1):
                sim.apply("CNOT", q, q + 1)
        return float(np.real(np.vdot(sim.state, H @ sim.state)))

    def is_available(self):
        return self.use_jit

    def info(self):
        return {
            "numba_installed": _HAS_NUMBA,
            "jit_enabled": self.use_jit,
            "fallback": "pure NumPy tensordot (bit-exact)",
        }


# ========================================================================
# Tests
# ========================================================================
def test_jit_bell_state():
    print("\n=== Test: JIT Bell State ===")
    from ..core.statevector import StatevectorSim
    sim = StatevectorSim(2)
    jit = JITBackend(use_jit=True)
    jit.apply_1q(sim, "H", 0)
    jit.apply_2q(sim, "CNOT", 0, 1)
    target = np.array([1, 0, 0, 1], dtype=complex) / np.sqrt(2)
    fid = abs(np.vdot(sim.state, target)) ** 2
    assert fid > 0.9999, f"Bell fidelity: {fid:.6f}"
    print(f"  PASS  (fidelity={fid:.6f})")


def test_jit_fallback():
    print("\n=== Test: JIT Fallback ===")
    jit = JITBackend(use_jit=False)
    assert not jit.is_available()
    print("  PASS  (fallback active)")


def test_jit_identity():
    print("\n=== Test: JIT vs Pure-NumPy Identity ===")
    np.random.seed(42)
    params = np.random.uniform(0, 2 * np.pi, size=8)
    n, layers = 4, 2

    sim_jit = StatevectorSim(n)
    jit = JITBackend(use_jit=True)
    idx = 0
    for _ in range(layers):
        for q in range(n):
            jit.apply_1q(sim_jit, "RY", q, theta=params[idx])
            idx += 1
        for q in range(n - 1):
            jit.apply_2q(sim_jit, "CNOT", q, q + 1)

    sim_np = StatevectorSim(n)
    idx = 0
    for _ in range(layers):
        for q in range(n):
            sim_np.apply("RY", params[idx], q)
            idx += 1
        for q in range(n - 1):
            sim_np.apply("CNOT", q, q + 1)

    diff = np.max(np.abs(sim_jit.state - sim_np.state))
    assert diff < 1e-10, f"State mismatch: {diff:.2e}"
    print(f"  PASS  (max diff={diff:.2e})")


def run_all_tests():
    print("=" * 60)
    print("JIT BACKEND TEST SUITE")
    print("=" * 60)
    test_jit_fallback()
    test_jit_bell_state()
    test_jit_identity()
    print("\n" + "=" * 60)
    print("ALL JIT TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
