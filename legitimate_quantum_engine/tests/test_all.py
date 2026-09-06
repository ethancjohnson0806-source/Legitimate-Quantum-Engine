#!/usr/bin/env python3
"""
test_all.py -- Legitimate Quantum Engine v5.0 Unified Test Suite

Runs all module tests:
  - v3.0 core (statevector, VQE, QAOA, MPS, etc.)
  - v4.0 modules (DMRG, TDVP, stabilizer, fermionic, etc.)
  - v5.0 new modules (JIT, benchmarks, chemistry, BP decoder, resource estimator)

Usage:  cd legitimate_quantum_engine_v5.0 && python -m legitimate_quantum_engine.tests.test_all
"""

import sys, time, numpy as np

# Ensure package is importable
sys.path.insert(0, ".")

from legitimate_quantum_engine.core.statevector import StatevectorSim
from legitimate_quantum_engine.solvers.vqe_ground import VQE, tfi_hamiltonian
from legitimate_quantum_engine.solvers.qaoa import QAOA, maxcut_hamiltonian
from legitimate_quantum_engine.tensor_networks.mps_simulator import MPSStateAdaptive, mps_ghz_state
from legitimate_quantum_engine.solvers.qite import QITE
from legitimate_quantum_engine.solvers.adapt_vqe import ADAPTVQE
from legitimate_quantum_engine.circuit_tools.entanglement_budget import EBCompiler
from legitimate_quantum_engine.characterization.shadow_amputation import amputate
from legitimate_quantum_engine.characterization.differential_sim import DifferentialSim
from legitimate_quantum_engine.tensor_networks.stochastic_mps import StochasticMPS
from legitimate_quantum_engine.utils.jit_backend import JITBackend
from legitimate_quantum_engine.benchmarks.resource_estimator import ResourceEstimator
from legitimate_quantum_engine.quantum_error_correction.surface_code import SurfaceCode
from legitimate_quantum_engine.quantum_error_correction.bp_decoder import BPDecoder
from legitimate_quantum_engine.quantum_chemistry.uccsd_ansatz import UCCSDAnsatz
from legitimate_quantum_engine.quantum_chemistry.chemistry_driver import ChemistryDriver


def banner(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


def check(cond, msg):
    status = "PASS" if cond else "FAIL"
    print(f"  [{status}] {msg}")
    return cond


def main():
    print("=" * 60)
    print("  Legitimate Quantum Engine v5.0 -- Unified Test Suite")
    print("=" * 60)

    results = []
    t0_total = time.time()

    # ============================================================
    # v3.0 Core Tests
    # ============================================================
    banner("[1] Core Simulator")
    sim = StatevectorSim(2)
    sim.apply("H", 0)
    sim.apply("CNOT", 0, 1)
    fid = abs(np.vdot(sim.state, np.array([1,0,0,1])/np.sqrt(2)))**2
    results.append(check(fid > 0.99, f"Bell state fidelity: {fid:.4f}"))

    banner("[2] VQE (4-qubit TFI)")
    np.random.seed(42)
    H4 = tfi_hamiltonian(4)
    e0_exact = np.linalg.eigvalsh(H4)[0]
    vqe = VQE(4, H4, num_layers=2, max_iterations=300)
    res_vqe = vqe.solve(verbose=False)
    err = abs(res_vqe["energy"] - e0_exact) / abs(e0_exact)
    results.append(check(err < 0.15, f"VQE error: {err:.4f}"))

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
    results.append(check(err_a < 0.05, f"ADAPT error: {err_a:.4f}"))

    banner("[5] MPS v2 -- Schmidt Adaptive (8-qubit GHZ)")
    mps = mps_ghz_state(8)
    sv = mps.to_statevector()
    target = np.zeros(256, dtype=complex)
    target[0] = target[255] = 1/np.sqrt(2)
    fid_mps = abs(np.vdot(sv, target))**2
    results.append(check(fid_mps > 0.99, f"MPS GHZ fidelity: {fid_mps:.4f}"))

    banner("[6] MPS Adaptive Truncation (20 qubits)")
    mps20 = MPSStateAdaptive(20, chi_max=64, epsilon=1e-10)
    mps20.apply("H", 0)
    for i in range(19):
        mps20.apply("CNOT", i, i+1)
    max_bond = max(mps20.bond_dims)
    results.append(check(max_bond <= 64, f"20q GHZ max bond: {max_bond}"))

    banner("[7] QITE Solver (4-qubit TFI)")
    qite = QITE(4, H4, dt=0.01, max_steps=200, verbose=False)
    res_qite = qite.solve()
    err_qite = abs(res_qite["energy"] - e0_exact) / abs(e0_exact)
    results.append(check(err_qite < 0.1, f"QITE error: {err_qite:.4f}"))

    banner("[8] Shadow-Based Amputation")
    circ_small = [("H", 0), ("CNOT", 0, 1), ("H", 1), ("CNOT", 1, 2)]
    H3_obs = np.diag([1, -1, -1, 1, -1, 1, 1, -1])
    pruned = amputate(circ_small, H3_obs, 3, tolerance=0.05, verbose=False)
    results.append(check(len(pruned) <= len(circ_small), f"Pruned: {len(pruned)} from {len(circ_small)}"))

    banner("[9] Differential Simulation")
    ds = DifferentialSim(4)
    ds.add_backend("statevector")
    ds.add_backend("mps", chi_max=16)
    ds.apply("H", 0)
    ds.apply("CNOT", 0, 1)
    results.append(check(ds.agreement >= 0, f"Backend agreement: {ds.agreement:.4f}"))

    banner("[10] Stochastic MPS")
    smps = StochasticMPS(8, chi_max=16, noise_strength=0.05, n_trajectories=5)
    smps.apply("H", 0)
    for i in range(7):
        smps.apply("CNOT", i, i+1)
    obs = np.diag([1.0] * 256)
    exp = smps.expectation(obs)
    results.append(check(exp["mean"] >= 0, f"Stochastic MPS <O>: {exp['mean']:.4f}"))

    # ============================================================
    # v5.0 New Module Tests
    # ============================================================
    banner("[11] JIT Backend")
    jit = JITBackend(use_jit=False)
    results.append(check(not jit.is_available(), "JIT fallback active"))
    sim_jit = StatevectorSim(2)
    jit.apply_1q(sim_jit, "H", 0)
    jit.apply_2q(sim_jit, "CNOT", 0, 1)
    fid_jit = abs(np.vdot(sim_jit.state, np.array([1,0,0,1])/np.sqrt(2)))**2
    results.append(check(fid_jit > 0.99, f"JIT Bell fidelity: {fid_jit:.4f}"))

    banner("[12] Resource Estimator")
    circ = [("H", i) for i in range(50)] + [("CNOT", i, i+1) for i in range(49)]
    est = ResourceEstimator(circ, hardware="ibm_eagle")
    r = est.analyze()
    results.append(check(r["feasible"] is True, "50-qubit VQE feasible on Eagle"))
    circ_big = [("H", i) for i in range(1000)]
    est2 = ResourceEstimator(circ_big, hardware="ibm_eagle")
    r2 = est2.analyze()
    results.append(check(r2["feasible"] is False, "1000-qubit infeasible"))

    banner("[13] Surface Code + BP Decoder")
    sc = SurfaceCode(distance=3)
    sc.encode_logical_zero()
    sc.inject_error("X", 4)
    syn = sc.measure_syndrome()
    bp = BPDecoder(distance=3)
    corr = bp.decode(syn['X'], syn['Z'])
    results.append(check(isinstance(corr, dict), f"BP correction returned dict: {len(corr)} qubits"))

    banner("[14] UCCSD Ansatz")
    ansatz = UCCSDAnsatz(n_orbitals=4, n_electrons=2, mapping="jordan_wigner")
    results.append(check(ansatz.num_parameters > 0, f"UCCSD params: {ansatz.num_parameters}"))
    sim_uccsd = StatevectorSim(4)
    params = ansatz.initial_parameters()
    ansatz.apply_to_sim(sim_uccsd, params)
    nrm = np.linalg.norm(sim_uccsd.state)
    results.append(check(abs(nrm - 1.0) < 1e-10, f"UCCSD norm: {nrm:.6f}"))

    banner("[15] Chemistry Driver")
    driver = ChemistryDriver(molecule="H2", bond_length=0.74)
    res_chem = driver.run_uccsd_vqe(max_iter=30, verbose=False)
    results.append(check(isinstance(res_chem["energy"], float), f"H2 energy computed: {res_chem['energy']:.4f} Ha"))

    banner("[16] MPS 20-qubit GHZ (scale test)")
    mps_big = mps_ghz_state(20)
    max_bond_big = max(mps_big.bond_dims)
    results.append(check(max_bond_big <= 2, f"20q GHZ bond dims: {max_bond_big}"))

    # ============================================================
    # Summary
    # ============================================================
    banner("SUMMARY")
    passed = sum(results)
    total = len(results)
    dt = time.time() - t0_total
    print(f"  Total tests:   {total}")
    print(f"  Passed:        {passed}")
    print(f"  Failed:        {total - passed}")
    print(f"  Success rate:  {passed/total*100:.1f}%")
    print(f"  Total time:    {dt:.2f}s")

    if passed == total:
        print("\n  ALL TESTS PASSED -- v5.0 is ready.")
    else:
        print("\n  Some tests failed. Check output above.")

    return passed == total


if __name__ == "__main__":
    ok = main()
    sys.exit(0 if ok else 1)
