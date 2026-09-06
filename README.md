# Legitimate Quantum Engine (LQE) v5.0.0

## Pure NumPy Quantum Computing that Runs on Your Phone

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
![Tests](https://img.shields.io/badge/Tests-19%2F19%20Passing-brightgreen)
![Python](https://img.shields.io/badge/Python-3.8+-blue?logo=python)

**A pure-NumPy quantum computing framework. 53 modules. Zero heavy dependencies. Built for learning, prototyping, and reference.**

LQE is built to run on a phone — no Qiskit, no Cirq, no heavy toolchains required. Every module is pure NumPy with optional Numba JIT acceleration. No Qiskit, no Cirq, no heavy toolchains. Just `import numpy` and go.

---

## Quick Start

### 1. Bell State -- Two Qubits, Instant Entanglement

```python
from legitimate_quantum_engine import StatevectorSim

sim = StatevectorSim(2)
sim.apply("H", 0)
sim.apply("CNOT", 0, 1)
print(sim.state)
# [0.707+0.j  0.000+0.j  0.000+0.j  0.707+0.j]
```

### 2. Auto-Solve -- Let the Engine Pick the Best Solver

```python
from legitimate_quantum_engine import auto_solve, tfi_hamiltonian

H = tfi_hamiltonian(4)
result = auto_solve(H, n_qubits=4)
print(f"Ground state energy: {result['energy']:.4f}")
print(f"Solver used: {result['solver_used']}")
```

### 3. Interactive Shell -- No Code Required

```bash
python shell.py
> new 2
> h 0
> cnot 0 1
> state
> probs
> quit
```

---

## Installation

### Option A: Clone and Run (No Install Needed)

```bash
git clone https://github.com/ethancjohnson0806-source/Legitimate-Quantum-Engine.git
cd legitimate-quantum-engine
python -m legitimate_quantum_engine.tests.test_all
```

### Option B: pip Install (Editable)

```bash
git clone https://github.com/ethancjohnson0806-source/Legitimate-Quantum-Engine.git
cd legitimate-quantum-engine
pip install -e .
```

### Option C: Run on Your Phone (Termux)

```bash
pkg install python numpy
python -c "from legitimate_quantum_engine import StatevectorSim; s=StatevectorSim(2); s.apply('H',0); print(s.state)"
```

---

## Module Overview

| Subpackage | Modules | What It Does |
|---|---|---|
| `core/` | statevector, sparse_hamiltonian, stabilizer, noise_models | Simulation backends: exact, sparse, Clifford, noisy |
| `solvers/` | vqe_ground, vqe_excited, qaoa, adapt_vqe, qite, qng, orchestrator | Ground-state, excited-state, and auto-selecting solvers |
| `tensor_networks/` | mps_simulator, dmrg, tdvp, stochastic_mps, adaptive_trotter | MPS, DMRG, and time-evolution methods |
| `quantum_chemistry/` | fermionic_encoding, uccsd_ansatz, chemistry_driver | Molecular Hamiltonians and UCCSD-VQE |
| `quantum_error_correction/` | surface_code, mwpm_decoder, bp_decoder | Surface codes and decoders |
| `circuit_tools/` | qasm_export, dynamic_circuits, circuit_knitting, entanglement_budget, duality, zx_optimizer, solovay_kitaev | Circuit manipulation and optimization |
| `characterization/` | classical_shadows, shadow_tomography, shadow_amputation, quantum_volume, rb_suite, differential_sim | Tomography, benchmarking, cross-validation |
| `open_systems/` | lindblad | Lindbladian dynamics for noisy evolution |
| `monte_carlo/` | qmc | Variational Monte Carlo solver |
| `benchmarks/` | vqe_benchmarks, synthesis_benchmarks, resource_estimator | Performance and resource estimation |
| `utils/` | symmetry_solver, quantum_kernel, extended_gates, error_mitigation, gpu_accelerator, jit_backend | Utilities and optional acceleration |

**Total: 53 modules across 11 subpackages.**

---

## Running Tests

```bash
python -m legitimate_quantum_engine.tests.test_all
```

Expected output: **19/19 tests passing in ~1 second.**

---

## Honest Limitations

LQE is honest about what it can and cannot do. No false promises.

| Module | Limitation |
|---|---|
| `statevector.py` | n <= 16 qubits (2^16 amplitudes) |
| `mps_simulator.py` | Fixed maximum bond dimension |
| `dmrg.py` | Two-site algorithm only |
| `tdvp.py` | Single-site, first-order, no sweep |
| `stabilizer.py` | Clifford gates only (Gottesman-Knill) |
| `surface_code.py` | Distance d <= 7 exact simulation |
| `vqe_ground.py` | SPSA optimizer, ~15% tolerance on hard landscapes |
| `chemistry_driver.py` | STO-3G basis only; pre-computed integrals for H2, LiH, BeH2 |
| `qmc.py` | Product-state ansatz only |
| `lindblad.py` | n <= 6 qubits |
| `zx_optimizer.py` | Basic spider fusion only |
| `solovay_kitaev.py` | Single-qubit gates only |

---

## Philosophy

1. **Pure NumPy.** Every core module uses only `numpy`. Optional dependencies (Numba) are wrapped in try/except and gracefully fall back.
2. **Phone-runnable.** If it cannot run on a $40 Android phone in Termux, it does not belong in core.
3. **Test-first.** Every module has inline tests. The unified suite validates the entire engine in under 2 seconds.
4. **Honest limitations.** We document what does not work, how far it scales, and when to use a heavier framework.

---

## Contributing

Pull requests welcome. All changes must pass `python -m legitimate_quantum_engine.tests.test_all` with 19/19 tests.

---

## License

MIT License -- see [LICENSE](LICENSE) for details.

---

*Built with persistence, pure NumPy, and the belief that quantum computing should be accessible to everyone.*
