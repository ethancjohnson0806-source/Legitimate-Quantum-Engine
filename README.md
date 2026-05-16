# Legitimate Quantum Engine: A State-Vector Quantum Simulator

A classical quantum circuit simulator implementing standard quantum algorithms and error mitigation techniques. This is a **state-vector simulator**, not a quantum hardware emulator or a revolutionary optimization framework.

## What This Is

- ✅ A working quantum circuit simulator using state-vector representation
- ✅ Implementations of standard algorithms: VQE, QAOA, Grover's search
- ✅ Common error mitigation techniques: ZNE, REM, PEC
- ✅ Support for 2-20 qubits (limited by exponential memory growth)
- ✅ Educational tool for learning quantum computing concepts
- ✅ Research platform for algorithm development

## What This Is NOT

- ❌ A replacement for real quantum hardware
- ❌ A revolutionary optimization framework with novel techniques
- ❌ A system that achieves "3000x speedup" (that claim was misleading)
- ❌ Hardware-verified to match IBM Quantum fidelity
- ❌ Suitable for production quantum computing applications

## Honest Performance Characteristics

### Execution Speed

| Operation | Time | Notes |
|-----------|------|-------|
| Single gate application | ~0.1ms | CPU-based, no GPU |
| 4-qubit VQE (20 iterations) | 47ms | Standard optimization |
| 4-qubit QAOA (20 iterations) | 4ms | Fast convergence |
| Grover's (3 qubits) | 0.1ms | Minimal computation |

**Important:** These times are for classical simulation. Real quantum hardware has different constraints (queue times, circuit depth limits, coherence windows). Comparing classical simulation time to quantum queue time is not a valid speedup metric.

### Memory Limitations

| Qubits | State Dimension | Memory Required | Practical Limit |
|--------|-----------------|-----------------|-----------------|
| 10 | 1,024 | 8 KB | ✅ Easy |
| 15 | 32,768 | 256 KB | ✅ Practical |
| 20 | 1,048,576 | 8 MB | ⚠️ Feasible |
| 25 | 33,554,432 | 256 MB | ❌ Difficult |
| 30 | 1,073,741,824 | 8 GB | ❌ Impractical |

This is a **fundamental limitation of state-vector simulation**, not a flaw in this implementation.

### Fidelity

- **Simulated fidelity with IBM noise model:** ~88% (on small circuits)
- **Real IBM Quantum hardware fidelity:** 85-92% (varies by backend)
- **Status:** We simulate IBM's noise model; we have NOT verified this matches real hardware

The fidelity numbers are based on our noise model simulation, not on actual comparison with IBM Quantum hardware.

## Core Components

### Quantum Gates
- Single-qubit: H, X, Y, Z, RX, RY, RZ, S, T
- Two-qubit: CNOT, CZ, SWAP, iSWAP
- Three-qubit: Toffoli, Fredkin

### Algorithms
- **VQE** (Variational Quantum Eigensolver) - Find ground state energy
- **QAOA** (Quantum Approximate Optimization Algorithm) - Solve optimization problems
- **Grover's Algorithm** - Database search

### Error Mitigation
- **ZNE** (Zero-Noise Extrapolation) - Reduce gate errors
- **REM** (Readout Error Mitigation) - Correct measurement errors
- **PEC** (Probabilistic Error Cancellation) - Cancel gate errors

These are standard techniques, not novel innovations.

### Advanced Algorithms
- **VQD** (Variational Quantum Deflation) - Compute excited states
- **ADAPT-VQE** (Adaptive VQE) - Automatically build ansatz circuits
- **QAOA+** (Enhanced QAOA) - Warm-starting for better convergence

### Optimization Techniques
1. **Clifford Detection** - Identify and optimize Clifford circuits (standard)
2. **Sparse State Representation** - Store only non-zero amplitudes (standard)
3. **Tensor Network** - Factor large tensors (standard)
4. **Classical Shadows** - Efficient state tomography (standard)
5. **Measurement Prediction** - Predict outcomes without full simulation (standard)
6. **Entanglement Routing** - Optimize qubit connectivity (standard)
7. **Error Mitigation** - ZNE, REM, PEC (standard)

**Note:** These are well-known optimization techniques used in quantum simulators. They are not novel contributions.

## Installation

### Requirements
- Python 3.8+
- NumPy, SciPy

### Setup
```bash
git clone https://github.com/ethancjohnson0806-source/Legitimate-Quantum-Engine.git
cd Legitimate-Quantum-Engine
pip install numpy scipy
```

### Optional Dependencies
```bash
# GPU support (NVIDIA CUDA)
pip install cupy-cuda11x  # Replace 11x with your CUDA version

# Web API
pip install fastapi uvicorn
```

## Quick Start

### Basic Usage
```python
from legitimate_quantum_engine.quantum_engine_v5_unified import QuantumEngineV5
import numpy as np

# Create simulator
engine = QuantumEngineV5(num_qubits=4, use_gpu=False)

# Create a simple Hamiltonian
H = np.diag(np.random.randn(16))
H = (H + H.T) / 2

# Run VQE
result = engine.run_vqe(H, iterations=50)
print(f"Ground state energy: {result['optimal_energy']:.6f}")

# Run QAOA
result = engine.run_qaoa(H, iterations=50)
print(f"Optimal cost: {result['optimal_cost']:.6f}")

# Run Grover's search
result = engine.run_grover_search([3, 5])
print(f"Success probability: {result['total_marked_probability']:.4f}")
```

### Web API
```bash
# Start server
python -m legitimate_quantum_engine.quantum_api_server

# Submit job
curl -X POST "http://localhost:8000/jobs/vqe?num_qubits=4&iterations=50"

# Check status
curl "http://localhost:8000/jobs/{job_id}"
```

## File Structure

```
legitimate_quantum_engine/
├── quantum_extended_gates.py           # Gate implementations
├── quantum_problem_solvers.py          # VQE, QAOA, Grover's
├── quantum_error_mitigation.py         # Error correction techniques
├── quantum_advanced_algorithms.py      # VQD, ADAPT-VQE, QAOA+
├── quantum_advanced_noise_models.py    # Realistic noise simulation
├── quantum_distributed_computing.py    # Parameter sweep framework
├── quantum_ibm_integration.py          # IBM Quantum interface
├── quantum_novel_optimization_techniques.py  # Optimization methods
├── quantum_api_server.py               # Web API
└── quantum_engine_v5_unified.py        # Main orchestration
```

## Limitations

### Hard Limits
- **Maximum qubits:** ~20 (due to exponential memory growth)
- **No quantum advantage:** This is classical simulation; no speedup over classical algorithms for most problems
- **No real hardware:** This simulates quantum behavior; it's not a real quantum computer

### Design Constraints
- **State-vector only:** Cannot handle very large circuits
- **Noise is simulated:** Based on theoretical models, not measured from real hardware
- **Single-threaded:** Limited parallelization
- **No distributed execution:** All computation on single machine

## What You Can Use This For

✅ **Learning quantum computing** - Understand how quantum circuits work  
✅ **Algorithm development** - Test VQE, QAOA, Grover's locally  
✅ **Error mitigation research** - Experiment with ZNE, REM, PEC  
✅ **Educational demonstrations** - Show quantum concepts to students  
✅ **Prototyping** - Before running on real hardware  

## What You Should NOT Use This For

❌ **Production quantum computing** - Use real quantum hardware (IBM, IonQ, Rigetti)  
❌ **Large-scale simulations** - Use specialized simulators (Qiskit Aer, PennyLane)  
❌ **Quantum advantage claims** - This is classical simulation  
❌ **Hardware benchmarking** - Use actual quantum computers  

## Testing

Run the test suite:
```bash
python -m legitimate_quantum_engine.quantum_integration_tests
```

**Test Results:** 11/14 tests pass (78.6%)
- ✅ Core algorithms working
- ✅ Error mitigation functional
- ✅ Noise models operational
- ⚠️ Some advanced features have edge cases

See `quantum_test_results.txt` for detailed results.

## Documentation

- **GETTING_STARTED.md** - Beginner's guide with examples
- **QUANTUM_ENGINE_DOCUMENTATION.md** - Technical reference
- **QUANTUM_ENGINE_ENHANCEMENTS_DOCUMENTATION.md** - Advanced features
- **PROOF_OF_CLAIMS.md** - Verification of performance claims
- **quantum_communities.md** - Community resources

## Comparison with Other Simulators

| Feature | This Engine | Qiskit Aer | PennyLane | Cirq |
|---------|-------------|-----------|-----------|------|
| State-vector | ✅ | ✅ | ✅ | ✅ |
| Error mitigation | ✅ | ✅ | ✅ | ✅ |
| VQE/QAOA | ✅ | ✅ | ✅ | ✅ |
| GPU support | ⚠️ | ✅ | ✅ | ✅ |
| Distributed | ❌ | ✅ | ✅ | ✅ |
| Production-ready | ❌ | ✅ | ✅ | ✅ |
| Community | Small | Large | Large | Large |

**Recommendation:** For production use, consider Qiskit Aer, PennyLane, or Cirq. This engine is best for learning and experimentation.

## Contributing

Contributions are welcome! Areas for improvement:
- GPU acceleration optimization
- Additional error mitigation techniques
- More quantum algorithms
- Performance optimizations
- Documentation improvements

## License

MIT License - See LICENSE file for details

## Citation

If you use this simulator in research, please cite:

```bibtex
@software{legitimate_quantum_engine_2026,
  title={Legitimate Quantum Engine: A State-Vector Quantum Simulator},
  author={Johnson, Ethan Caleb},
  year={2026},
  url={https://github.com/ethancjohnson0806-source/Legitimate-Quantum-Engine}
}
```

## Disclaimer

This is a **classical quantum simulator**, not a quantum computer. It cannot solve problems faster than classical computers. The performance metrics are for classical simulation only. Fidelity claims are based on simulated noise models, not verified against real quantum hardware.

Use this tool for learning, research, and experimentation. For production quantum computing, use real quantum hardware or established simulators like Qiskit Aer.

## Support

For issues, questions, or suggestions:
- Open an issue on GitHub
- Check the documentation files
- Review test results in `quantum_test_results.txt`

---

**Last Updated:** May 15, 2026  
**Version:** 5.1.0  
**Status:** Educational/Research Tool
