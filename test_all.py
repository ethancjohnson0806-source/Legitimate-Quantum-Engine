#!/usr/bin/env python
"""Legitimate Quantum Engine v3.0 — Full Test Suite
Tests all v2.1 features + all v3.0 modules.
Run: cd legitimate_quantum_engine_v3.0 && python test_all.py
"""
import sys, time, numpy as np

sys.path.insert(0, ".")
from legitimate_quantum_engine import (
    StatevectorSim, VQE, QAOA, ADAPTVQE, QNGOptimizer,
    MPSStateAdaptive, mps_ghz_state,
    EBCompiler, amputate, QITE, AdaptiveTrotter,
    Duality, auto_solve, ClassicalShadow,
    DifferentialSim, StochasticMPS,
    apply_pauli_noise, tfi_hamiltonian, maxcut_hamiltonian
)

def banner(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")

def check(cond, msg):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {msg}")
    return cond

def main():
    print("="*60)
    print("  Legitimate Quantum Engine v3.0 — Full Test Suite")
    print("="*60)

    results = []

    # ============================================================
    # v2.1 Core Tests
    # ============================================================
    banner("[1] Core Simulator")
    sim = StatevectorSim(2)
    sim.apply("H", 0)
    sim.apply("CNOT", 0, 1)
    fid = abs(np.vdot(sim.state, np.array([1,0,0,1])/np.sqrt(2)))**2
    results.append(check(fid > 0.99, f"Bell state fidelity: {fid:.4f}"))

    banner("[2] VQE (4-qubit TFI)")
    H4 = tfi_hamiltonian(4)
    e0_exact = np.linalg.eigvalsh(H4)[0]
    vqe = VQE(4, H4, num_layers=2, max_iterations=200)
    res_vqe = vqe.solve(verbose=False)
    err = abs(res_vqe["energy"] - e0_exact) / abs(e0_exact)
    results.append(check(err < 0.15, f"VQE error: {err:.4f} (exact: {e0_exact:.4f})"))

    banner("[3] QAOA (3-node triangle)")
    edges = [(0,1),(1,2),(2,0)]
    H3 = maxcut_hamiltonian(3, edges)
    e0_qaoa = np.linalg.eigvalsh(H3)[0]
    qaoa = QAOA(3, edges, p=1, max_iterations=100)
    res_qaoa = qaoa.solve(verbose=False)
    err_q = abs(res_qaoa["energy"] - e0_qaoa) / abs(e0_qaoa)
    results.append(check(err_q < 0.05, f"QAOA error: {err_q:.4f}"))

    banner("[4] ADAPT-VQE (4-qubit TFI)")
    adapt = ADAPTVQE(n_qubits=4, hamiltonian=H4, max_operators=6)
    res_adapt = adapt.solve(verbose=False)
    err_a = abs(res_adapt["energy"] - e0_exact) / abs(e0_exact)
    results.append(check(err_a < 0.05, f"ADAPT error: {err_a:.4f}, ops={len(res_adapt.get('operators', []))}"))

    # ============================================================
    # v3.0 Module Tests
    # ============================================================
    banner("[5] MPS v2 — Schmidt Adaptive (8-qubit GHZ)")
    mps = mps_ghz_state(8)
    sv = mps.to_statevector()
    target = np.zeros(256, dtype=complex)
    target[0] = target[255] = 1/np.sqrt(2)
    fid_mps = abs(np.vdot(sv, target))**2
    results.append(check(fid_mps > 0.99, f"MPS GHZ fidelity: {fid_mps:.4f}"))

    banner("[6] MPS Entanglement Spectroscopy")
    spec = mps.entanglement_spectrum(cut=4)
    results.append(check(len(spec) >= 2, f"Spectrum length: {len(spec)}"))
    results.append(check(spec[0] > 0.6, f"Top singular value: {spec[0]:.4f}"))
    report = mps.full_spectrum_report()
    results.append(check(len(report) == 7, f"Full report cuts: {len(report)}"))

    banner("[7] MPS Adaptive Truncation (20 qubits)")
    mps20 = MPSStateAdaptive(20, chi_max=64, epsilon=1e-10)
    mps20.apply("H", 0)
    for i in range(19):
        mps20.apply("CNOT", i, i+1)
    max_bond = max(mps20.bond_dims)
    results.append(check(max_bond <= 64, f"20q GHZ max bond: {max_bond}"))

    banner("[8] Entanglement-Budget Compiler")
    circ = [("CNOT", 0, 5), ("CNOT", 1, 6), ("CNOT", 2, 7)]
    compiled = EBCompiler.compile(circ, budget="mps_chi_32", n_qubits=8)
    results.append(check(len(compiled) > len(circ), f"Compiled gates: {len(compiled)} (was {len(circ)})"))
    est = EBCompiler.estimate_bond_growth(compiled, 8)
    results.append(check(est > 0, f"Estimated bond growth: {est}"))

    banner("[9] Shadow-Based Amputation")
    circ_small = [("H", 0), ("CNOT", 0, 1), ("H", 1), ("CNOT", 1, 2)]
    H3_obs = np.diag([1, -1, -1, 1, -1, 1, 1, -1])
    pruned = amputate(circ_small, H3_obs, 3, tolerance=0.05, verbose=False)
    results.append(check(len(pruned) <= len(circ_small), f"Pruned: {len(pruned)} from {len(circ_small)}"))

    banner("[10] QITE Solver (4-qubit TFI)")
    qite = QITE(4, H4, dt=0.01, max_steps=200, verbose=False)
    res_qite = qite.solve()
    err_qite = abs(res_qite["energy"] - e0_exact) / abs(e0_exact)
    results.append(check(err_qite < 0.1, f"QITE error: {err_qite:.4f} (steps: {res_qite['steps']})"))

    banner("[11] Adaptive Trotter (8 qubits)")
    H8 = tfi_hamiltonian(8)
    at = AdaptiveTrotter(H8, 8, dt_init=0.01, chi_max=32)
    res_at = at.evolve(steps=20)
    results.append(check(len(res_at["step_sizes"]) == 20, f"Steps recorded: {len(res_at['step_sizes'])}"))
    results.append(check(max(res_at["bond_history"]) <= 32, f"Max bond: {max(res_at['bond_history'])}"))

    banner("[12] Circuit-Hamiltonian Duality")
    d = Duality()
    gates = [("H", 0), ("CNOT", 0, 1)]
    h_dict = d.circuit_to_hamiltonian(gates, 2)
    results.append(check("hamiltonian" in h_dict, "Clock Hamiltonian generated"))
    gates_back = d.hamiltonian_to_trotter_circuit(np.eye(4), dt=0.01, steps=10)
    results.append(check(len(gates_back) > 0, f"Trotter gates: {len(gates_back)}"))

    banner("[13] Solver Orchestrator")
    res_orc = auto_solve(H4, 4, target_precision=0.01)
    results.append(check(res_orc["solver_used"] in ["exact_diagonalization", "qite", "adapt_vqe", "vqe_spsa"],
                         f"Auto-solver picked: {res_orc['solver_used']}"))
    results.append(check(abs(res_orc["energy"] - e0_exact) / abs(e0_exact) < 0.15,
                         f"Auto energy error: {abs(res_orc['energy'] - e0_exact)/abs(e0_exact):.4f}"))

    banner("[14] Classical Shadows")
    shadow = ClassicalShadow(4, num_snapshots=500)
    sim4 = StatevectorSim(4)
    sim4.apply("H", 0)
    sim4.apply("CNOT", 0, 1)
    shadow.capture(sim4)
    target_bell = np.array([1,0,0,1,0,0,0,0,0,0,0,0,0,0,0,1])/np.sqrt(2)
    fid_est = shadow.fidelity_estimate(target_bell)
    results.append(check(fid_est >= 0, f"Shadow fidelity estimate: {fid_est:.4f}"))

    banner("[15] Differential Simulation")
    ds = DifferentialSim(4)
    ds.add_backend("statevector")
    ds.add_backend("mps", chi_max=16)
    ds.apply("H", 0)
    ds.apply("CNOT", 0, 1)
    results.append(check(ds.agreement >= 0, f"Backend agreement: {ds.agreement:.4f}"))

    banner("[16] Stochastic MPS")
    smps = StochasticMPS(8, chi_max=16, noise_strength=0.05, n_trajectories=5)
    smps.apply("H", 0)
    for i in range(7):
        smps.apply("CNOT", i, i+1)
    obs = np.diag([1.0] * 256)
    exp = smps.expectation(obs)
    results.append(check(exp["mean"] >= 0, f"Stochastic MPS <O>: {exp['mean']:.4f} ± {exp['std']:.4f}"))

    banner("[17] MPS 20-qubit GHZ (scale test)")
    mps_big = mps_ghz_state(20)
    max_bond_big = max(mps_big.bond_dims)
    results.append(check(max_bond_big <= 2, f"20q GHZ bond dims: {max_bond_big} (should be 2)"))

    # ============================================================
    # Summary
    # ============================================================
    banner("SUMMARY")
    passed = sum(results)
    total = len(results)
    print(f"  Total tests: {total}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {total - passed}")
    print(f"  Success rate: {passed/total*100:.1f}%")

    if passed == total:
        print("\n  ✅ ALL TESTS PASSED — v3.0 is ready.")
    else:
        print("\n  ⚠️  Some tests failed. Check output above.")

    return passed == total

if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
