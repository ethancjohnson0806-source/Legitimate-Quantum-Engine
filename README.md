# Legitimate Quantum Engine v2.1

Honest, hackable, phone-runnable quantum simulation.

## What's New in v2.1

- **ADAPT-VQE**: Builds ansatz operator-by-operator; reaches chemical accuracy with fewer parameters.
- **MPS Backend**: Matrix Product State simulator for 20–50 qubits (low entanglement).
- **Quantum Natural Gradient (QNG)**: 3–10x faster VQE convergence using the Fubini-Study metric.
- **QAOA Warm Start**: Initialize from classical greedy solution instead of random.
- **Dynamic Circuits**: Mid-circuit measurement, reset, and conditional gates.

## Core Features (from v2.0)

- Fast statevector simulator (`tensordot`, not `np.kron`)
- SPSA-based VQE and QAOA solvers
- Quantum kernel / ZZ feature map
- Pauli noise models
- OpenQASM export
- Sparse simulator, classical shadows, error mitigation stubs

## Install

```bash
cd ~/legitimate_quantum_engine_v2.1
python test_all.py
```

## Quick Start

```python
from legitimate_quantum_engine import VQE, ADAPTVQE, QAOA, MPSState

# VQE
from legitimate_quantum_engine.vqe_solver import tfi_hamiltonian
H = tfi_hamiltonian(n=4)
solver = VQE(num_qubits=4, hamiltonian=H, num_layers=2)
print(solver.solve())

# ADAPT-VQE (higher accuracy)
adapt = ADAPTVQE(n_qubits=4, hamiltonian=H, max_operators=8)
print(adapt.solve())

# MPS (20 qubits)
mps = MPSState(20, bond_dim=32)
mps.apply("H", 0)
for i in range(19):
    mps.apply("CNOT", i, i+1)
print(mps.to_statevector()[:4])
```

## Requirements

- **NumPy only**. No scipy, no CUDA, no 500MB install.
- Optional: scipy (speeds up ADAPT-VQE parameter optimization).

## License

MIT / Public domain. Hack it.
