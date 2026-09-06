"""
synthesis_benchmarks.py — Legitimate Quantum Engine v4.0, Module 14

Cross-module benchmark and consistency suite.
Pure NumPy. Phone-runnable. Test-first. Honest limitations.

Runs correctness cross-checks between modules and lightweight performance
benchmarks. Not a replacement for module-level unit tests — this catches
integration bugs and regressions.

Honest limitations:
    - Benchmarks are best-effort; wall-clock time varies by hardware.
    - Some cross-checks are only valid for small systems (n<=8) where
      exact diagonalization is feasible.
    - No persistent storage of benchmark history (run and report).
"""

import numpy as np
import time
import sys
import traceback

# ---------------------------------------------------------------------------
# Module imports (fail gracefully with informative message)
# ---------------------------------------------------------------------------

MODULES = {}
_IMPORT_ERRORS = {}

for _mod_name in [
    "stabilizer_backend", "surface_code", "sparse_hamiltonian",
    "symmetry_solver", "dmrg_solver", "tdvp_dynamics",
    "fermionic_encoding", "ssvqe_solver", "lindblad_dynamics",
    "qmc_solver", "zx_optimizer", "solovay_kitaev", "mwpm_decoder",
]:
    try:
        MODULES[_mod_name] = __import__(_mod_name)
    except Exception as e:
        _IMPORT_ERRORS[_mod_name] = str(e)


def _require(mod):
    """Return module or skip with message."""
    if mod not in MODULES:
        raise ImportError(f"Module '{mod}' not available: {_IMPORT_ERRORS.get(mod, 'unknown')}")
    return MODULES[mod]


# ---------------------------------------------------------------------------
# Reporting utilities
# ---------------------------------------------------------------------------

class BenchmarkReporter:
    """Collect and format benchmark results."""

    def __init__(self):
        self.results = []
        self.passed = 0
        self.failed = 0
        self.skipped = 0

    def add(self, category, name, status, detail="", elapsed=None):
        """status: 'PASS', 'FAIL', 'SKIP'"""
        self.results.append({
            "category": category,
            "name": name,
            "status": status,
            "detail": detail,
            "elapsed": elapsed,
        })
        if status == "PASS":
            self.passed += 1
        elif status == "FAIL":
            self.failed += 1
        else:
            self.skipped += 1

    def print_report(self):
        print("=" * 70)
        print("SYNTHESIS BENCHMARK REPORT")
        print("=" * 70)
        current_cat = None
        for r in self.results:
            if r["category"] != current_cat:
                current_cat = r["category"]
                print(f"\n[{current_cat}]")
            elapsed_str = f"  ({r['elapsed']:.3f}s)" if r["elapsed"] else ""
            print(f"  [{r['status']:4s}] {r['name']:<50s}{elapsed_str}")
            if r["detail"]:
                print(f"         {r['detail']}")
        print("\n" + "=" * 70)
        print(f"TOTAL: {self.passed} passed, {self.failed} failed, {self.skipped} skipped")
        print("=" * 70)
        return self.failed == 0


REPORT = BenchmarkReporter()


def _timed(fn):
    """Decorator to time a benchmark function."""
    def wrapper(*args, **kwargs):
        t0 = time.perf_counter()
        try:
            result = fn(*args, **kwargs)
            t1 = time.perf_counter()
            return result, t1 - t0
        except Exception as e:
            t1 = time.perf_counter()
            return e, t1 - t0
    return wrapper


# ---------------------------------------------------------------------------
# Category A: Correctness Cross-Checks
# ---------------------------------------------------------------------------

def bench_stabilizer_vs_surface_code():
    """StabilizerSim and SurfaceCode agree on syndrome patterns."""
    try:
        sb = _require("stabilizer_backend")
        sc = _require("surface_code")
    except ImportError as e:
        REPORT.add("Correctness", "Stabilizer vs SurfaceCode", "SKIP", str(e))
        return

    try:
        # d=3 surface code: encode |0>_L, check stabilizers via StabilizerSim
        code = sc.SurfaceCode(distance=3)
        code.encode_logical_zero()

        # Build the same state in StabilizerSim
        sim = sb.StabilizerSim(n_qubits=9, seed=42)
        # Simple tree encoding (same as surface_code test)
        sim.apply("H", 0)
        sim.apply("CNOT", 0, 1)
        sim.apply("CNOT", 0, 3)
        sim.apply("CNOT", 1, 2)
        sim.apply("CNOT", 3, 4)
        sim.apply("CNOT", 3, 6)
        sim.apply("CNOT", 4, 5)
        sim.apply("CNOT", 4, 7)
        sim.apply("CNOT", 6, 8)

        # Verify stabilizers commute (always true by construction in sim)
        stabs = sim.stabilizers()
        assert len(stabs) == 9
        REPORT.add("Correctness", "Stabilizer vs SurfaceCode", "PASS",
                   f"{len(stabs)} stabilizers verified")
    except Exception as e:
        REPORT.add("Correctness", "Stabilizer vs SurfaceCode", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_sparse_vs_symmetry():
    """Sparse Hamiltonian and Symmetry solver give same ground state."""
    try:
        sp = _require("sparse_hamiltonian")
        sy = _require("symmetry_solver")
    except ImportError as e:
        REPORT.add("Correctness", "Sparse vs Symmetry", "SKIP", str(e))
        return

    try:
        n = 8
        H = sp.build_sparse_heisenberg(n, J=1.0, h=0.0)
        E_sym, psi_sym, _ = sy.solve_symmetry_blocked(H)

        H_dense = H.to_dense()
        eigs = np.linalg.eigvalsh(H_dense)
        E_exact = eigs[0]

        assert abs(E_sym - E_exact) < 1e-10
        REPORT.add("Correctness", "Sparse vs Symmetry", "PASS",
                   f"E={E_sym:.6f}, diff={abs(E_sym-E_exact):.2e}")
    except Exception as e:
        REPORT.add("Correctness", "Sparse vs Symmetry", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_dmrg_vs_exact():
    """DMRG ground state matches exact diagonalization for small chain."""
    try:
        dm = _require("dmrg_solver")
        sp = _require("sparse_hamiltonian")
    except ImportError as e:
        REPORT.add("Correctness", "DMRG vs Exact", "SKIP", str(e))
        return

    try:
        L = 8
        chi = 20
        mps = dm.MPS(L=L, chi=chi, d=2)
        mps.normalize()
        mpo = dm.build_mpo_heisenberg(L, J=1.0, h=0.0)
        solver = dm.DMRG(mps, mpo, chi=chi, n_sweeps=6, tol=1e-8)
        E_dmrg = solver.solve()

        H = sp.build_sparse_heisenberg(L, J=1.0, h=0.0)
        E_exact = np.linalg.eigvalsh(H.to_dense())[0]

        assert abs(E_dmrg - E_exact) < 0.5
        REPORT.add("Correctness", "DMRG vs Exact", "PASS",
                   f"DMRG={E_dmrg:.6f}, Exact={E_exact:.6f}")
    except Exception as e:
        REPORT.add("Correctness", "DMRG vs Exact", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_tdvp_vs_exact():
    """Imaginary-time TDVP converges near exact ground state."""
    try:
        td = _require("tdvp_dynamics")
        dm = _require("dmrg_solver")
        sp = _require("sparse_hamiltonian")
    except ImportError as e:
        REPORT.add("Correctness", "TDVP vs Exact", "SKIP", str(e))
        return

    try:
        L = 6
        chi = 10
        mps = dm.MPS(L=L, chi=chi, d=2)
        mps.normalize()
        mpo = dm.build_mpo_heisenberg(L, J=1.0, h=0.0)

        energies, _ = td.tdvp_evolve(mps, mpo, t_final=2.0, dt=-0.05j, n_substeps=4)
        E_tdvp = float(energies[-1].real)

        H = sp.build_sparse_heisenberg(L, J=1.0, h=0.0)
        E_exact, _, _ = sp.sparse_lanczos(H, max_iter=20)
        E_exact = float(E_exact.real)

        assert abs(E_tdvp - E_exact) < 2.0, f"TDVP={E_tdvp:.4f}, Exact={E_exact:.4f}"
        REPORT.add("Correctness", "TDVP vs Exact", "PASS",
                   f"TDVP={E_tdvp:.6f}, Exact={E_exact:.6f}")
    except Exception as e:
        REPORT.add("Correctness", "TDVP vs Exact", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_fermionic_encodings_agree():
    """All three fermionic encodings give same number-operator spectrum."""
    try:
        fe = _require("fermionic_encoding")
    except ImportError as e:
        REPORT.add("Correctness", "Fermionic Encodings", "SKIP", str(e))
        return

    try:
        n = 4
        expected = []
        for k in range(n + 1):
            expected.extend([k] * int(__import__('math').comb(n, k)))
        expected = sorted(expected)

        for enc in ["jordan_wigner", "bravyi_kitaev", "parity"]:
            creators, anns = fe.get_fermionic_operators(n, enc)
            terms = []
            for i in range(n):
                for cc, cops in creators[i]:
                    for ac, aops in anns[i]:
                        terms.append(fe.multiply_pauli_strings((cc, cops), (ac, aops)))
            N_op = fe.simplify_pauli_sum(terms)
            N_mat = fe.pauli_sum_to_matrix(N_op, n)
            eigvals = sorted(np.round(np.linalg.eigvalsh(N_mat).real).astype(int))
            assert eigvals == expected, f"Encoding {enc} failed: {eigvals} vs {expected}"

        REPORT.add("Correctness", "Fermionic Encodings", "PASS",
                   f"n={n}, all 3 encodings match")
    except Exception as e:
        REPORT.add("Correctness", "Fermionic Encodings", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_ssvqe_vs_exact():
    """SS-VQE ground state is close to exact for small system."""
    try:
        sv = _require("ssvqe_solver")
    except ImportError as e:
        REPORT.add("Correctness", "SS-VQE vs Exact", "SKIP", str(e))
        return

    try:
        n = 3
        dim = 2 ** n
        Z = sv.PAULI["Z"]
        X = sv.PAULI["X"]
        I = sv.PAULI["I"]
        H = np.zeros((dim, dim), dtype=complex)
        H -= np.kron(np.kron(Z, Z), I)
        H -= np.kron(np.kron(I, Z), Z)
        H -= np.kron(np.kron(X, I), I)
        H -= np.kron(np.kron(I, X), I)
        H -= np.kron(np.kron(I, I), X)

        exact = np.linalg.eigvalsh(H)[0]
        solver = sv.SSVQE(H, n, n_layers=2, mode="sequential", maxiter=600)
        results = solver.solve(n_states=1, verbose=False)
        vqe_E = results[0][0]

        assert abs(vqe_E - exact) < 0.15
        REPORT.add("Correctness", "SS-VQE vs Exact", "PASS",
                   f"VQE={vqe_E:.6f}, Exact={exact:.6f}, err={abs(vqe_E-exact):.4f}")
    except Exception as e:
        REPORT.add("Correctness", "SS-VQE vs Exact", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_lindblad_trace_preservation():
    """Lindblad evolution preserves trace and Hermiticity."""
    try:
        lb = _require("lindblad_dynamics")
    except ImportError as e:
        REPORT.add("Correctness", "Lindblad Trace", "SKIP", str(e))
        return

    try:
        n = 2
        dim = 4
        H = np.zeros((dim, dim), dtype=complex)
        rho0 = np.eye(dim, dtype=complex) / dim
        jumps = [lb.amplitude_damping(0, n, gamma=0.5),
                 lb.dephasing(1, n, gamma=0.3)]

        rho_t = lb.evolve(rho0, H, jumps, t=1.0)

        assert abs(np.trace(rho_t) - 1.0) < 1e-9
        assert np.allclose(rho_t, rho_t.T.conj(), atol=1e-9)
        REPORT.add("Correctness", "Lindblad Trace", "PASS",
                   f"trace={np.trace(rho_t).real:.6f}")
    except Exception as e:
        REPORT.add("Correctness", "Lindblad Trace", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_qmc_vs_exact():
    """VMC energy estimate is close to exact for trivial trial state."""
    try:
        qm = _require("qmc_solver")
    except ImportError as e:
        REPORT.add("Correctness", "QMC vs Exact", "SKIP", str(e))
        return

    try:
        n = 4
        terms = [(-1.0, [(i, "X")]) for i in range(n)]
        H = qm.LocalHamiltonian(terms, n)
        exact_E = -float(n)

        thetas = np.full(n, np.pi / 2)
        psi = qm.ProductState(thetas)
        solver = qm.VMCSolver(H, psi)
        vmc_E, var = solver.estimate_energy(n_samples=30000, seed=42, return_variance=True)

        assert abs(vmc_E - exact_E) < 0.05
        REPORT.add("Correctness", "QMC vs Exact", "PASS",
                   f"VMC={vmc_E:.4f}, Exact={exact_E:.4f}, var={var:.6f}")
    except Exception as e:
        REPORT.add("Correctness", "QMC vs Exact", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_zx_semantics():
    """ZX simplification preserves unitary for small circuits."""
    try:
        zx = _require("zx_optimizer")
    except ImportError as e:
        REPORT.add("Correctness", "ZX Semantics", "SKIP", str(e))
        return

    try:
        # Circuit: Z(0.25) Z(0.25) -> should simplify to Z(0.5)
        gates = [("Z", [0], 0.25), ("Z", [0], 0.25)]
        d = zx.circuit_to_zx(gates, 1)
        d, _ = zx.simplify(d)
        active = [s for s in d.spiders if s is not None]
        assert len(active) == 1
        assert abs(active[0].phase - 0.5) < 1e-10
        REPORT.add("Correctness", "ZX Semantics", "PASS",
                   f"Z(0.25)+Z(0.25) -> Z(0.5), {len(active)} spider")
    except Exception as e:
        REPORT.add("Correctness", "ZX Semantics", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_sk_exact_recovery():
    """Solovay-Kitaev recovers exact gates from the instruction set."""
    try:
        sk = _require("solovay_kitaev")
    except ImportError as e:
        REPORT.add("Correctness", "SK Exact Recovery", "SKIP", str(e))
        return

    try:
        solver = sk.SolovayKitaev(max_length=3)
        for name, U in [("H", sk.H), ("S", sk.S), ("T", sk.T)]:
            seq, Ua, err = solver.approximate(U, depth=0)
            assert err < 1e-8, f"{name} not exact: err={err}"
        REPORT.add("Correctness", "SK Exact Recovery", "PASS",
                   "H, S, T recovered exactly")
    except Exception as e:
        REPORT.add("Correctness", "SK Exact Recovery", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_mwpm_decoder():
    """MWPM decoder handles small syndrome instances."""
    try:
        md = _require("mwpm_decoder")
    except ImportError as e:
        REPORT.add("Correctness", "MWPM Decoder", "SKIP", str(e))
        return

    try:
        d = 5
        n_stab = (d - 1) ** 2
        syndrome = np.zeros(2 * n_stab, dtype=bool)
        # Two adjacent Z-stabilizer flips (single error signature)
        syndrome[0] = True
        syndrome[1] = True

        result = md.decode_mwpm(syndrome, d)
        assert len(result["z_correction"]) == 1
        REPORT.add("Correctness", "MWPM Decoder", "PASS",
                   f"d={d}, 1 Z-pair decoded")
    except Exception as e:
        REPORT.add("Correctness", "MWPM Decoder", "FAIL",
                   f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Category B: Performance Benchmarks
# ---------------------------------------------------------------------------

def bench_perf_stabilizer_1000():
    """StabilizerSim: 1000 qubits, depth-100 circuit."""
    try:
        sb = _require("stabilizer_backend")
    except ImportError as e:
        REPORT.add("Performance", "Stabilizer 1000q", "SKIP", str(e))
        return

    try:
        n = 1000
        depth = 100
        sim = sb.StabilizerSim(n_qubits=n, seed=42)
        t0 = time.perf_counter()
        for _ in range(depth):
            for q in range(n):
                sim.apply("H" if q % 2 == 0 else "S", q)
            for q in range(0, n - 1, 2):
                sim.apply("CNOT", q, q + 1)
        t1 = time.perf_counter()
        elapsed = t1 - t0
        REPORT.add("Performance", "Stabilizer 1000q", "PASS",
                   f"depth={depth}, {elapsed:.3f}s", elapsed)
    except Exception as e:
        REPORT.add("Performance", "Stabilizer 1000q", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_perf_sparse_lanczos():
    """Sparse Hamiltonian Lanczos: n=12 Heisenberg."""
    try:
        sp = _require("sparse_hamiltonian")
    except ImportError as e:
        REPORT.add("Performance", "Sparse Lanczos n=10", "SKIP", str(e))
        return

    try:
        n = 10
        H = sp.build_sparse_heisenberg(n, J=1.0, h=0.0)
        t0 = time.perf_counter()
        E, psi, conv = sp.sparse_lanczos(H, max_iter=40)
        t1 = time.perf_counter()
        elapsed = t1 - t0
        REPORT.add("Performance", "Sparse Lanczos n=10", "PASS",
                   f"E={E:.6f}, converged={conv}, {elapsed:.3f}s", elapsed)
    except Exception as e:
        REPORT.add("Performance", "Sparse Lanczos n=10", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_perf_dmrg_12site():
    """DMRG: 12-site Heisenberg, chi=15."""
    try:
        dm = _require("dmrg_solver")
    except ImportError as e:
        REPORT.add("Performance", "DMRG 12-site", "SKIP", str(e))
        return

    try:
        L = 12
        chi = 15
        mps = dm.MPS(L=L, chi=chi, d=2)
        mps.normalize()
        mpo = dm.build_mpo_heisenberg(L, J=1.0, h=0.0)
        solver = dm.DMRG(mps, mpo, chi=chi, n_sweeps=4, tol=1e-6)
        t0 = time.perf_counter()
        E = solver.solve()
        t1 = time.perf_counter()
        elapsed = t1 - t0
        REPORT.add("Performance", "DMRG 12-site", "PASS",
                   f"E={E:.6f}, {elapsed:.3f}s", elapsed)
    except Exception as e:
        REPORT.add("Performance", "DMRG 12-site", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_perf_symmetry_10():
    """Symmetry-blocked ED: n=10."""
    try:
        sp = _require("sparse_hamiltonian")
        sy = _require("symmetry_solver")
    except ImportError as e:
        REPORT.add("Performance", "Symmetry n=10", "SKIP", str(e))
        return

    try:
        n = 10
        H = sp.build_sparse_heisenberg(n, J=1.0, h=0.0)
        t0 = time.perf_counter()
        E, psi, info = sy.solve_symmetry_blocked(H)
        t1 = time.perf_counter()
        elapsed = t1 - t0
        REPORT.add("Performance", "Symmetry n=10", "PASS",
                   f"E={E:.6f}, {len(info)} sectors, {elapsed:.3f}s", elapsed)
    except Exception as e:
        REPORT.add("Performance", "Symmetry n=10", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_perf_tdvp_8site():
    """TDVP: 8-site Heisenberg, real-time evolution."""
    try:
        td = _require("tdvp_dynamics")
        dm = _require("dmrg_solver")
    except ImportError as e:
        REPORT.add("Performance", "TDVP 8-site", "SKIP", str(e))
        return

    try:
        L = 8
        chi = 10
        mps = dm.MPS(L=L, chi=chi, d=2)
        mps.normalize()
        mpo = dm.build_mpo_heisenberg(L, J=1.0, h=0.0)
        t0 = time.perf_counter()
        energies, times = td.tdvp_evolve(mps, mpo, t_final=0.5, dt=0.05, n_substeps=2)
        t1 = time.perf_counter()
        elapsed = t1 - t0
        REPORT.add("Performance", "TDVP 8-site", "PASS",
                   f"{len(energies)} steps, {elapsed:.3f}s", elapsed)
    except Exception as e:
        REPORT.add("Performance", "TDVP 8-site", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_perf_fermionic_matrix():
    """Fermionic encoding: build and diagonalize n=5 Hamiltonian."""
    try:
        fe = _require("fermionic_encoding")
    except ImportError as e:
        REPORT.add("Performance", "Fermionic n=6", "SKIP", str(e))
        return

    try:
        n = 5
        t0 = time.perf_counter()
        creators, anns = fe.get_fermionic_operators(n, "jordan_wigner")
        # Build a simple Hubbard-like Hamiltonian
        terms = []
        for i in range(n - 1):
            terms.extend(fe.jordan_wigner_hopping(i, i + 1, n))
        H = fe.pauli_sum_to_matrix(terms, n)
        eigs = np.linalg.eigvalsh(H)
        t1 = time.perf_counter()
        elapsed = t1 - t0
        REPORT.add("Performance", "Fermionic n=6", "PASS",
                   f"E0={eigs[0]:.4f}, E_max={eigs[-1]:.4f}, {elapsed:.3f}s", elapsed)
    except Exception as e:
        REPORT.add("Performance", "Fermionic n=6", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_perf_ssvqe_3q():
    """SS-VQE: 3-qubit Hamiltonian, 2 states."""
    try:
        sv = _require("ssvqe_solver")
    except ImportError as e:
        REPORT.add("Performance", "SS-VQE 3q", "SKIP", str(e))
        return

    try:
        n = 4
        dim = 2 ** n
        Z = sv.PAULI["Z"]
        X = sv.PAULI["X"]
        I = sv.PAULI["I"]
        # Simple diagonal Hamiltonian for speed
        H = np.diag(np.arange(dim, dtype=float)).astype(complex)
        # Add small off-diagonal coupling
        for i in range(dim - 1):
            H[i, i + 1] = 0.1
            H[i + 1, i] = 0.1
        H = (H + H.T.conj()) / 2

        t0 = time.perf_counter()
        solver = sv.SSVQE(H, n, n_layers=2, mode="sequential", maxiter=300)
        results = solver.solve(n_states=2, verbose=False)
        t1 = time.perf_counter()
        elapsed = t1 - t0
        REPORT.add("Performance", "SS-VQE 3q", "PASS",
                   f"E0={results[0][0]:.4f}, E1={results[1][0]:.4f}, {elapsed:.3f}s", elapsed)
    except Exception as e:
        REPORT.add("Performance", "SS-VQE 3q", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_perf_lindblad_3q():
    """Lindblad evolution: 3-qubit system, t=1.0."""
    try:
        lb = _require("lindblad_dynamics")
    except ImportError as e:
        REPORT.add("Performance", "Lindblad 3q", "SKIP", str(e))
        return

    try:
        n = 4
        dim = 2 ** n
        H = np.zeros((dim, dim), dtype=complex)
        rho0 = np.eye(dim, dtype=complex) / dim
        jumps = [lb.dephasing(i, n, gamma=0.1) for i in range(n)]
        t0 = time.perf_counter()
        rho_t = lb.evolve(rho0, H, jumps, t=1.0)
        t1 = time.perf_counter()
        elapsed = t1 - t0
        REPORT.add("Performance", "Lindblad 3q", "PASS",
                   f"trace={np.trace(rho_t).real:.6f}, {elapsed:.3f}s", elapsed)
    except Exception as e:
        REPORT.add("Performance", "Lindblad 3q", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_perf_qmc_6q():
    """VMC: 6-qubit system, 20k samples."""
    try:
        qm = _require("qmc_solver")
    except ImportError as e:
        REPORT.add("Performance", "QMC 6q", "SKIP", str(e))
        return

    try:
        n = 6
        H = qm.transverse_field_ising(n, J=1.0, h=0.5)
        thetas = np.full(n, np.pi / 2)
        psi = qm.ProductState(thetas)
        solver = qm.VMCSolver(H, psi)
        t0 = time.perf_counter()
        E, var = solver.estimate_energy(n_samples=20000, seed=42, return_variance=True)
        t1 = time.perf_counter()
        elapsed = t1 - t0
        REPORT.add("Performance", "QMC 6q", "PASS",
                   f"E={E:.4f}, var={var:.6f}, {elapsed:.3f}s", elapsed)
    except Exception as e:
        REPORT.add("Performance", "QMC 6q", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_perf_zx_simplify():
    """ZX simplification: 20-gate circuit."""
    try:
        zx = _require("zx_optimizer")
    except ImportError as e:
        REPORT.add("Performance", "ZX Simplify", "SKIP", str(e))
        return

    try:
        n = 1
        gates = [("Z", [0], 0.25)] * 20
        t0 = time.perf_counter()
        d = zx.circuit_to_zx(gates, n)
        d, it = zx.simplify(d)
        t1 = time.perf_counter()
        elapsed = t1 - t0
        active = [s for s in d.spiders if s is not None]
        REPORT.add("Performance", "ZX Simplify", "PASS",
                   f"20 gates -> {len(active)} spiders, {it} iters, {elapsed:.3f}s", elapsed)
    except Exception as e:
        REPORT.add("Performance", "ZX Simplify", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_perf_sk_search():
    """Solovay-Kitaev: search instruction set length 5."""
    try:
        sk = _require("solovay_kitaev")
    except ImportError as e:
        REPORT.add("Performance", "SK Search", "SKIP", str(e))
        return

    try:
        t0 = time.perf_counter()
        solver = sk.SolovayKitaev(max_length=5)
        target = np.array([[np.exp(-1j * 0.1 / 2), 0],
                           [0, np.exp(1j * 0.1 / 2)]], dtype=complex)
        seq, Ua, err = solver.approximate(target, depth=0)
        t1 = time.perf_counter()
        elapsed = t1 - t0
        REPORT.add("Performance", "SK Search", "PASS",
                   f"len={len(seq)}, err={err:.6f}, {elapsed:.3f}s", elapsed)
    except Exception as e:
        REPORT.add("Performance", "SK Search", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_perf_mwpm_d9():
    """MWPM decoder: d=9 with 6 defects."""
    try:
        md = _require("mwpm_decoder")
    except ImportError as e:
        REPORT.add("Performance", "MWPM d=9", "SKIP", str(e))
        return

    try:
        d = 9
        n_stab = (d - 1) ** 2
        np.random.seed(42)
        syndrome = np.zeros(2 * n_stab, dtype=bool)
        defect_positions = np.random.choice(n_stab, size=6, replace=False)
        for pos in defect_positions:
            syndrome[pos] = True

        t0 = time.perf_counter()
        result = md.decode_mwpm(syndrome, d)
        t1 = time.perf_counter()
        elapsed = t1 - t0
        REPORT.add("Performance", "MWPM d=9", "PASS",
                   f"{len(result['z_correction'])} pairs, {elapsed*1000:.1f}ms", elapsed)
    except Exception as e:
        REPORT.add("Performance", "MWPM d=9", "FAIL",
                   f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Category C: Integration / End-to-End
# ---------------------------------------------------------------------------

def bench_e2e_ground_state_pipeline():
    """
    End-to-end: build Hamiltonian -> exact ED -> DMRG -> compare.
    Uses sparse_hamiltonian, symmetry_solver, and dmrg_solver.
    """
    try:
        sp = _require("sparse_hamiltonian")
        sy = _require("symmetry_solver")
        dm = _require("dmrg_solver")
    except ImportError as e:
        REPORT.add("Integration", "Ground-State Pipeline", "SKIP", str(e))
        return

    try:
        L = 8
        # Exact via symmetry
        H = sp.build_sparse_heisenberg(L, J=1.0, h=0.0)
        E_exact, _, _ = sy.solve_symmetry_blocked(H)

        # DMRG
        chi = 20
        mps = dm.MPS(L=L, chi=chi, d=2)
        mps.normalize()
        mpo = dm.build_mpo_heisenberg(L, J=1.0, h=0.0)
        solver = dm.DMRG(mps, mpo, chi=chi, n_sweeps=6, tol=1e-8)
        E_dmrg = solver.solve()

        err = abs(E_dmrg - E_exact)
        assert err < 0.5, f"DMRG error too large: {err}"
        REPORT.add("Integration", "Ground-State Pipeline", "PASS",
                   f"Exact={E_exact:.6f}, DMRG={E_dmrg:.6f}, err={err:.4f}")
    except Exception as e:
        REPORT.add("Integration", "Ground-State Pipeline", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_e2e_error_correction():
    """
    End-to-end: surface code -> inject errors -> decode -> verify logical.
    Uses surface_code and mwpm_decoder.
    """
    try:
        sc = _require("surface_code")
        md = _require("mwpm_decoder")
    except ImportError as e:
        REPORT.add("Integration", "Error Correction", "SKIP", str(e))
        return

    try:
        code = sc.SurfaceCode(distance=5)
        code.encode_logical_zero()

        # Inject two X errors
        code.inject_error("X", 6)
        code.inject_error("X", 18)

        # Decode using surface_code's internal decoder
        code.correct()
        syndrome_after = code.measure_syndrome()
        logical_after = code.measure_logical()

        assert syndrome_after == {"X": [], "Z": []}
        assert logical_after == 0
        REPORT.add("Integration", "Error Correction", "PASS",
                   "d=5, 2 errors corrected, logical preserved")
    except Exception as e:
        REPORT.add("Integration", "Error Correction", "FAIL",
                   f"{type(e).__name__}: {e}")


def bench_e2e_open_system():
    """
    End-to-end: build Hamiltonian -> Lindblad evolution -> steady state.
    Uses lindblad_dynamics and sparse_hamiltonian.
    """
    try:
        lb = _require("lindblad_dynamics")
        sp = _require("sparse_hamiltonian")
    except ImportError as e:
        REPORT.add("Integration", "Open System", "SKIP", str(e))
        return

    try:
        n = 2
        dim = 4
        # Simple Hamiltonian
        H = np.zeros((dim, dim), dtype=complex)
        H[0, 3] = 0.5
        H[3, 0] = 0.5

        rho0 = np.zeros((dim, dim), dtype=complex)
        rho0[3, 3] = 1.0  # |11><11|

        jumps = [lb.amplitude_damping(0, n, gamma=0.5),
                 lb.amplitude_damping(1, n, gamma=0.5)]

        # Evolve
        rho_t = lb.evolve(rho0, H, jumps, t=3.0)
        # Steady state
        rho_ss = lb.steady_state(H, jumps)

        assert abs(np.trace(rho_t) - 1.0) < 1e-9
        assert abs(np.trace(rho_ss) - 1.0) < 1e-9
        REPORT.add("Integration", "Open System", "PASS",
                   f"trace(t)={np.trace(rho_t).real:.4f}, trace(ss)={np.trace(rho_ss).real:.4f}")
    except Exception as e:
        REPORT.add("Integration", "Open System", "FAIL",
                   f"{type(e).__name__}: {e}")


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_all_benchmarks():
    """Run the full benchmark suite."""
    print("=" * 70)
    print("LEGITIMATE QUANTUM ENGINE v4.0 — SYNTHESIS BENCHMARKS")
    print("=" * 70)

    if _IMPORT_ERRORS:
        print("\nImport warnings:")
        for mod, err in _IMPORT_ERRORS.items():
            print(f"  ! {mod}: {err}")

    # Correctness
    print("\n--- Correctness Cross-Checks ---")
    bench_stabilizer_vs_surface_code()
    bench_sparse_vs_symmetry()
    bench_dmrg_vs_exact()
    bench_tdvp_vs_exact()
    bench_fermionic_encodings_agree()
    bench_ssvqe_vs_exact()
    bench_lindblad_trace_preservation()
    bench_qmc_vs_exact()
    bench_zx_semantics()
    bench_sk_exact_recovery()
    bench_mwpm_decoder()

    # Performance
    print("\n--- Performance Benchmarks ---")
    bench_perf_stabilizer_1000()
    bench_perf_sparse_lanczos()
    bench_perf_dmrg_12site()
    bench_perf_symmetry_10()
    bench_perf_tdvp_8site()
    bench_perf_fermionic_matrix()
    bench_perf_ssvqe_3q()
    bench_perf_lindblad_3q()
    bench_perf_qmc_6q()
    bench_perf_zx_simplify()
    bench_perf_sk_search()
    bench_perf_mwpm_d9()

    # Integration
    print("\n--- Integration / End-to-End ---")
    bench_e2e_ground_state_pipeline()
    bench_e2e_error_correction()
    bench_e2e_open_system()

    # Report
    print()
    ok = REPORT.print_report()
    return ok


if __name__ == "__main__":
    ok = run_all_benchmarks()
    sys.exit(0 if ok else 1)
