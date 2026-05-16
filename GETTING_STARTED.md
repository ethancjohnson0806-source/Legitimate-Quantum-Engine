# Legitimate Quantum Engine - Getting Started Guide

**Author:** Manus AI  
**Version:** 5.1.0  
**Last Updated:** May 2026

---

## Table of Contents

1. [Installation](#installation)
2. [Quick Start](#quick-start)
3. [Basic Concepts](#basic-concepts)
4. [Core Workflows](#core-workflows)
5. [Advanced Features](#advanced-features)
6. [Troubleshooting](#troubleshooting)
7. [Next Steps](#next-steps)

---

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- 2GB RAM minimum (4GB recommended)

### Install from PyPI

```bash
pip install legitimate-quantum-engine
```

### Install from Source

```bash
git clone https://github.com/ethancjohnson0806-source/Legitimate-Quantum-Engine.git
cd Legitimate-Quantum-Engine
pip install -e .
```

### Verify Installation

```bash
python3 -c "from legitimate_quantum_engine.quantum_engine_v5_unified import QuantumEngine; print('✓ Installation successful!')"
```

---

## Quick Start

### Your First Quantum Circuit

Create a simple two-qubit circuit and measure it:

```python
from legitimate_quantum_engine.quantum_engine_v5_unified import QuantumEngine, QuantumCircuit

# Create a quantum engine with 2 qubits
engine = QuantumEngine(num_qubits=2)

# Create a circuit
circuit = QuantumCircuit(num_qubits=2)
circuit.h(0)  # Hadamard gate on qubit 0
circuit.cnot(0, 1)  # CNOT gate: control=0, target=1

# Simulate the circuit
state = engine.simulate(circuit.to_dict())
print(f"State vector: {state}")

# Measure 1000 times
counts = engine.measure(circuit.to_dict(), shots=1000)
print(f"Measurement results: {counts}")
```

**Expected Output:**
```
State vector: [0.707+0.j 0.   +0.j 0.   +0.j 0.707+0.j]
Measurement results: {'00': 489, '11': 511}
```

This creates a Bell state (maximally entangled state) where measurements always show either `00` or `11` with equal probability.

---

## Basic Concepts

### Quantum Circuit

A quantum circuit is a sequence of quantum gates applied to qubits. The engine represents circuits as dictionaries:

```python
circuit_dict = {
    "num_qubits": 2,
    "gates": [
        {"name": "h", "qubits": [0], "params": []},
        {"name": "cnot", "qubits": [0, 1], "params": []}
    ]
}
```

### Supported Gates

| Gate | Type | Description | Parameters |
|------|------|-------------|------------|
| **h** | Single | Hadamard gate | None |
| **x** | Single | Pauli-X (NOT) gate | None |
| **y** | Single | Pauli-Y gate | None |
| **z** | Single | Pauli-Z gate | None |
| **rx** | Single | Rotation around X | angle (radians) |
| **ry** | Single | Rotation around Y | angle (radians) |
| **rz** | Single | Rotation around Z | angle (radians) |
| **cnot** | Two | Controlled-NOT | None |
| **cx** | Two | Controlled-X (same as CNOT) | None |
| **cz** | Two | Controlled-Z | None |
| **swap** | Two | Swap qubits | None |
| **toffoli** | Three | Controlled-Controlled-NOT | None |

### State Vector

The state vector represents the quantum state of all qubits. For N qubits, it has 2^N complex amplitudes:

```python
# 2-qubit state vector has 4 amplitudes
state = [a00, a01, a10, a11]  # Complex numbers

# Probability of measuring |00⟩ is |a00|²
# Probability of measuring |01⟩ is |a01|²
# etc.
```

### Measurement

Measurement collapses the quantum state to a classical bit string. The probability of each outcome is determined by the state vector:

```python
counts = engine.measure(circuit, shots=1000)
# Returns: {'00': 500, '11': 500} (approximate)
```

---

## Core Workflows

### Workflow 1: Variational Quantum Eigensolver (VQE)

VQE finds the ground state energy of a Hamiltonian by optimizing a parameterized circuit:

```python
import numpy as np
from legitimate_quantum_engine.quantum_engine_v5_unified import QuantumEngine

# Define a Hamiltonian (2x2 matrix for 1 qubit)
H = np.array([
    [1, 0],
    [0, -1]
])

# Create engine
engine = QuantumEngine(num_qubits=1)

# Define ansatz (parameterized circuit)
def ansatz(params):
    circuit = {
        "num_qubits": 1,
        "gates": [
            {"name": "ry", "qubits": [0], "params": [params[0]]}
        ]
    }
    return circuit

# Define cost function
def cost_function(params):
    circuit = ansatz(params)
    state = engine.simulate(circuit)
    energy = np.real(state.conj() @ H @ state)
    return energy

# Optimize
from scipy.optimize import minimize
result = minimize(cost_function, x0=[0.5], method='COBYLA')

print(f"Ground state energy: {result.fun:.4f}")
print(f"Optimal parameters: {result.x}")
```

**Expected Output:**
```
Ground state energy: -1.0000
Optimal parameters: [3.1416]
```

### Workflow 2: Quantum Approximate Optimization Algorithm (QAOA)

QAOA solves combinatorial optimization problems:

```python
from legitimate_quantum_engine.quantum_advanced_algorithms import EnhancedQAOA
import numpy as np

# Create QAOA instance
qaoa = EnhancedQAOA(num_qubits=3)

# Define cost Hamiltonian (MaxCut example)
cost_H = np.array([
    [0, 1, 1, 0, 1, 0, 0, 0],
    [1, 0, 0, 1, 0, 1, 0, 0],
    [1, 0, 0, 1, 0, 0, 1, 0],
    [0, 1, 1, 0, 0, 0, 0, 1],
    [1, 0, 0, 0, 0, 1, 1, 0],
    [0, 1, 0, 0, 1, 0, 0, 1],
    [0, 0, 1, 0, 1, 0, 0, 1],
    [0, 0, 0, 1, 0, 1, 1, 0]
])

# Run QAOA
result = qaoa.run_qaoa_plus(cost_H, np.eye(8), num_layers=3)

print(f"Best cost: {result.optimal_value:.4f}")
print(f"Approximation ratio: {result.metadata['approximation_ratio']:.2%}")
```

### Workflow 3: Grover's Search Algorithm

Grover's algorithm finds marked items in an unsorted database:

```python
from legitimate_quantum_engine.quantum_engine_v5_unified import QuantumEngine

engine = QuantumEngine(num_qubits=3)

# Mark item |101⟩ (5 in decimal)
marked_state = [0, 0, 0, 0, 0, 1, 0, 0]

# Run Grover's algorithm
result = engine.grovers_algorithm(marked_state, num_iterations=2)

print(f"Found state: {result['found_state']}")
print(f"Success probability: {result['success_probability']:.2%}")
```

---

## Advanced Features

### Feature 1: Error Mitigation

Reduce errors from realistic hardware noise:

```python
from legitimate_quantum_engine.quantum_advanced_noise_models import RealisticQuantumSimulator, NoiseModelLibrary

# Create simulator with IBM Quantum noise
noise_model = NoiseModelLibrary.ibm_quantum_model()
simulator = RealisticQuantumSimulator(num_qubits=3, noise_model=noise_model)

# Simulate circuit with noise
circuit = {...}  # Your circuit
counts_noisy = simulator.simulate_with_noise(circuit, shots=1000)

# Compare with ideal
engine = QuantumEngine(num_qubits=3)
counts_ideal = engine.measure(circuit, shots=1000)

print(f"Ideal: {counts_ideal}")
print(f"Noisy: {counts_noisy}")
```

### Feature 2: Distributed Parameter Sweep

Explore parameter space in parallel:

```python
from legitimate_quantum_engine.quantum_distributed_computing import DistributedQuantumExecutor
import numpy as np

# Create distributed executor with 4 nodes
executor = DistributedQuantumExecutor(num_nodes=4)

# Define parameter ranges
param_ranges = {
    "theta": np.linspace(0, 2*np.pi, 20),
    "phi": np.linspace(0, np.pi, 10)
}

# Submit sweep
job_id = executor.submit_parameter_sweep(
    base_circuit,
    param_ranges,
    circuit_builder_func
)

# Check status
status = executor.get_job_status(job_id)
print(f"Completed: {status['completed_tasks']}/{status['total_tasks']}")

# Get results
results = executor.get_aggregated_results(job_id)
print(f"Best parameters: {results['best_result']}")
```

### Feature 3: Excited States with VQD

Compute multiple eigenvalues:

```python
from legitimate_quantum_engine.quantum_advanced_algorithms import VariationalQuantumDeflation
import numpy as np

# Create VQD instance for 3 states
vqd = VariationalQuantumDeflation(num_qubits=2, num_states=3)

# Hamiltonian
H = np.array([
    [1, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, 0],
    [0, 0, 0, -1]
])

# Run VQD
results = vqd.run_vqd(H, ansatz_func, initial_params, iterations=100)

# Print eigenvalues
for i, result in enumerate(results):
    print(f"E_{i} = {result.optimal_value:.6f}")
```

### Feature 4: IBM Quantum Hardware

Execute on real quantum computers:

```python
from legitimate_quantum_engine.quantum_ibm_integration import IBMQuantumBridge, IBMQuantumConfig

# Configure IBM Quantum connection
config = IBMQuantumConfig(
    api_token="your_ibm_token",
    backend_name="ibm_fez",  # or another backend
    max_qubits=5
)

# Create bridge
bridge = IBMQuantumBridge(config)

# Transpile circuit for hardware
circuit = {...}
transpiled = bridge.transpile_circuit(circuit)

# Estimate fidelity
fidelity = bridge.estimate_hardware_fidelity(circuit)
print(f"Estimated fidelity: {fidelity:.2%}")

# Execute on hardware
result = bridge.execute_on_hardware(circuit, shots=1024)
print(f"Job ID: {result['job_id']}")
```

---

## Troubleshooting

### Issue: "ModuleNotFoundError: No module named 'quantum_engine_v5_unified'"

**Solution:** Install the package correctly:
```bash
pip install legitimate-quantum-engine
# Then import from the package:
from legitimate_quantum_engine.quantum_engine_v5_unified import QuantumEngine
```

### Issue: "Circuit dimension mismatch"

**Solution:** Ensure circuit qubits match engine qubits:
```python
engine = QuantumEngine(num_qubits=3)  # 3 qubits
circuit = {
    "num_qubits": 3,  # Must match!
    "gates": [...]
}
```

### Issue: "Optimization not converging"

**Solution:** Try different initialization or optimization settings:
```python
# Use better initial parameters
initial_params = np.random.randn(num_params) * 0.1

# Try different optimizer
result = minimize(cost_func, initial_params, method='L-BFGS-B')

# Or use barren plateau mitigation
from legitimate_quantum_engine.quantum_novel_optimization_techniques import BarrenPlateauMitigation
bp = BarrenPlateauMitigation(num_qubits)
result = bp.run_barren_plateau_mitigation(cost_func)
```

---

## Next Steps

1. **Explore Examples:** Check the [GitHub repository](https://github.com/ethancjohnson0806-source/Legitimate-Quantum-Engine) for more examples

2. **Read Documentation:** See [QUANTUM_ENGINE_MEGA_COCKTAIL_DOCS.md](https://github.com/ethancjohnson0806-source/Legitimate-Quantum-Engine/blob/main/QUANTUM_ENGINE_MEGA_COCKTAIL_DOCS.md) for detailed API reference

3. **Try Advanced Techniques:** Experiment with:
   - Barren plateau mitigation
   - KFAC optimization
   - Quantum kernel methods
   - Distributed computing

4. **Join the Community:** Star the repository and contribute improvements

5. **Report Issues:** Found a bug? [Open an issue](https://github.com/ethancjohnson0806-source/Legitimate-Quantum-Engine/issues)

---

## Quick Reference

### Common Imports

```python
# Core engine
from legitimate_quantum_engine.quantum_engine_v5_unified import QuantumEngine, QuantumCircuit

# Algorithms
from legitimate_quantum_engine.quantum_advanced_algorithms import (
    VariationalQuantumDeflation,
    ADAPTVariationalQuantumEigensolver,
    EnhancedQAOA
)

# Noise modeling
from legitimate_quantum_engine.quantum_advanced_noise_models import (
    RealisticQuantumSimulator,
    NoiseModelLibrary
)

# Optimization
from legitimate_quantum_engine.quantum_novel_optimization_techniques import (
    BarrenPlateauMitigation,
    QuantumNeuralNetworkOptimizer
)

# Distributed computing
from legitimate_quantum_engine.quantum_distributed_computing import DistributedQuantumExecutor

# IBM Quantum
from legitimate_quantum_engine.quantum_ibm_integration import IBMQuantumBridge
```

### Common Patterns

```python
# Create engine
engine = QuantumEngine(num_qubits=3)

# Create circuit
circuit = QuantumCircuit(num_qubits=3)
circuit.h(0)
circuit.cnot(0, 1)

# Simulate
state = engine.simulate(circuit.to_dict())

# Measure
counts = engine.measure(circuit.to_dict(), shots=1000)

# Optimize
from scipy.optimize import minimize
result = minimize(cost_function, x0=[0.5], method='COBYLA')
```

---

## Support

- **Documentation:** https://github.com/ethancjohnson0806-source/Legitimate-Quantum-Engine
- **Issues:** https://github.com/ethancjohnson0806-source/Legitimate-Quantum-Engine/issues
- **Email:** ethancjohnson0806@gmail.com

---

*Last updated: May 2026 | Legitimate Quantum Engine V5.1.0*
