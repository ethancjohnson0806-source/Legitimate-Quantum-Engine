# Qiskit Integration Strategy for LegitimateQuantumEngine

This document outlines the strategy for integrating the `LegitimateQuantumEngine` with IBM Quantum hardware via Qiskit. The goal is to enable the engine to execute quantum circuits on real quantum processors or their high-fidelity simulators, thereby bridging the gap between local simulation and cloud-based quantum computing.

## 1. Qiskit Installation and Setup

Qiskit is the primary open-source SDK for working with IBM Quantum systems. It will be installed in the sandbox environment.

```bash
sudo pip3 install qiskit qiskit-ibm-provider
```

## 2. IBM Quantum Account Authentication

To access IBM Quantum hardware, users need an IBM Quantum account and an API token. The authentication process will involve:

*   **API Token Storage**: The user's API token will be loaded securely. Qiskit provides `IBMProvider.save_account()` to store credentials locally, and `IBMProvider()` to load them.
*   **Backend Selection**: Users will be able to select a specific backend (e.g., a real quantum device or a simulator like `ibmq_qasm_simulator`) for circuit execution.

## 3. Modifying the `LegitimateQuantumEngine`

The `LegitimateQuantumEngine` will be extended to include a new method for running circuits on Qiskit backends. This will primarily affect the `run_rcs_and_compute_xeb` function, as XEB is a prime candidate for hardware execution.

### **3.1. Circuit Translation**

The existing `generate_random_circuit` method outputs a list of tuples representing gates. This format needs to be translated into a Qiskit `QuantumCircuit` object.

*   **Single-qubit gates**: `H`, `RX`, `RZ` will be mapped directly to Qiskit's `h()`, `rx()`, `rz()` methods.
*   **Two-qubit gates**: `CZ` will be mapped to Qiskit's `cz()` method.

### **3.2. Backend Execution**

A new function, e.g., `run_qiskit_circuit_on_backend(circuit, backend_name, shots)`, will be added to handle:

1.  **Loading IBM Provider**: `from qiskit_ibm_provider import IBMProvider; provider = IBMProvider()`
2.  **Getting Backend**: `backend = provider.get_backend(backend_name)`
3.  **Transpilation**: Optimizing the circuit for the target backend using `transpile()`.
4.  **Job Submission**: `job = backend.run(transpiled_circuit, shots=shots)`
5.  **Result Retrieval**: `result = job.result()`
6.  **Measurement Counts**: Extracting measurement counts from the results.

### **3.3. XEB Calculation with Hardware Results**

The `run_rcs_and_compute_xeb` method will be updated to optionally use hardware results. The XEB calculation will then use the measurement counts from the hardware to estimate the fidelity.

## 4. User Guide for IBM Quantum Account

A separate markdown document will be created to guide the user through:

1.  Creating an IBM Quantum account.
2.  Obtaining their API token.
3.  Saving the API token using `IBMProvider.save_account()`.
4.  Selecting an appropriate backend (e.g., `ibmq_qasm_simulator` for initial testing).

## 5. Refactoring the `LegitimateQuantumEngine` for Hardware Mode

The `evolve` method will be modified to include a flag (e.g., `use_hardware=False`). When `use_hardware` is `True`, the XEB calculation will leverage the Qiskit integration for execution on a specified backend. This will allow for direct comparison between local simulation and hardware execution.
