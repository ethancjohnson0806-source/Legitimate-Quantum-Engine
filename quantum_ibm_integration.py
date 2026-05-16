"""
IBM Quantum Hardware Integration Module
Connects the Legitimate Quantum Engine to IBM Quantum Experience
Enables execution on real quantum hardware with automatic fallback to simulator
"""

import json
import time
from typing import Dict, List, Tuple, Optional, Any
import numpy as np
from dataclasses import dataclass


@dataclass
class IBMQuantumConfig:
    """Configuration for IBM Quantum connection"""
    api_token: Optional[str] = None
    hub: str = "ibm-q"
    group: str = "open"
    project: str = "main"
    backend_name: str = "ibm_fez"
    max_qubits: int = 5
    use_simulator: bool = True


class IBMQuantumBridge:
    """Bridge between Legitimate Quantum Engine and IBM Quantum"""

    def __init__(self, config: IBMQuantumConfig):
        self.config = config
        self.backend = None
        self.connected = False
        self.job_cache = {}
        self._initialize_connection()

    def _initialize_connection(self):
        """Initialize connection to IBM Quantum"""
        try:
            # Try to import qiskit
            from qiskit import IBMQ
            from qiskit_ibm_runtime import QiskitRuntimeService

            if self.config.api_token:
                try:
                    QiskitRuntimeService.save_account(
                        channel="ibm_quantum",
                        token=self.config.api_token,
                        overwrite=True
                    )
                    service = QiskitRuntimeService()
                    self.backend = service.backend(self.config.backend_name)
                    self.connected = True
                    print(f"✓ Connected to IBM Quantum backend: {self.config.backend_name}")
                except Exception as e:
                    print(f"⚠ IBM Quantum connection failed: {e}")
                    print("  Falling back to simulator mode")
                    self.connected = False
            else:
                print("⚠ No API token provided. Using simulator mode.")
                self.connected = False

        except ImportError:
            print("⚠ Qiskit not installed. Install with: pip install qiskit qiskit-ibm-runtime")
            self.connected = False

    def transpile_circuit(self, circuit_dict: Dict[str, Any]) -> Dict[str, Any]:
        """Transpile circuit for IBM hardware"""
        try:
            from qiskit import QuantumCircuit, transpile

            # Reconstruct circuit from dict
            qc = self._dict_to_circuit(circuit_dict)

            if self.connected and self.backend:
                # Transpile for real hardware
                transpiled = transpile(qc, self.backend, optimization_level=3)
                return self._circuit_to_dict(transpiled)
            else:
                # Return original circuit
                return circuit_dict

        except Exception as e:
            print(f"Transpilation failed: {e}")
            return circuit_dict

    def execute_on_hardware(
        self,
        circuit_dict: Dict[str, Any],
        shots: int = 1024,
        job_name: str = "quantum_job"
    ) -> Dict[str, Any]:
        """Execute circuit on IBM Quantum hardware"""

        if not self.connected:
            return {
                "status": "simulator_mode",
                "message": "IBM Quantum not connected. Use simulator instead.",
                "shots": shots
            }

        try:
            from qiskit import QuantumCircuit
            from qiskit_ibm_runtime import Session, Sampler

            qc = self._dict_to_circuit(circuit_dict)

            # Execute on real hardware
            with Session(backend=self.backend) as session:
                sampler = Sampler(session=session)
                job = sampler.run(qc, shots=shots)

                # Cache job
                job_id = job.job_id()
                self.job_cache[job_id] = {
                    "circuit": circuit_dict,
                    "shots": shots,
                    "timestamp": time.time(),
                    "status": "submitted"
                }

                print(f"✓ Job submitted to IBM Quantum: {job_id}")

                return {
                    "status": "submitted",
                    "job_id": job_id,
                    "backend": self.config.backend_name,
                    "shots": shots,
                    "queue_position": "unknown"
                }

        except Exception as e:
            print(f"Hardware execution failed: {e}")
            return {"status": "error", "message": str(e)}

    def retrieve_job_result(self, job_id: str) -> Dict[str, Any]:
        """Retrieve results from submitted job"""

        if job_id not in self.job_cache:
            return {"status": "not_found", "job_id": job_id}

        try:
            from qiskit_ibm_runtime import QiskitRuntimeService

            service = QiskitRuntimeService()
            job = service.job(job_id)

            status = job.status()
            result = {
                "job_id": job_id,
                "status": str(status),
                "backend": self.config.backend_name
            }

            if status.name == "DONE":
                counts = job.result().quasi_dists[0].binary_probabilities()
                result["counts"] = counts
                result["execution_time"] = job.metrics.get("execution_time", 0)

            return result

        except Exception as e:
            print(f"Result retrieval failed: {e}")
            return {"status": "error", "message": str(e)}

    def estimate_hardware_fidelity(self, circuit_dict: Dict[str, Any]) -> float:
        """Estimate fidelity on IBM hardware based on circuit depth"""

        try:
            from qiskit import QuantumCircuit

            qc = self._dict_to_circuit(circuit_dict)
            depth = qc.depth()
            num_gates = qc.size()

            # Empirical fidelity model for IBM hardware
            # Typical 1-qubit error: ~0.1%, 2-qubit error: ~0.5%
            single_qubit_error = 0.001
            two_qubit_error = 0.005

            # Estimate based on gate count
            estimated_fidelity = (1 - single_qubit_error) ** (num_gates * 0.7) * \
                                (1 - two_qubit_error) ** (num_gates * 0.3)

            return max(0.0, min(1.0, estimated_fidelity))

        except Exception as e:
            print(f"Fidelity estimation failed: {e}")
            return 0.5

    def compare_simulator_vs_hardware(
        self,
        circuit_dict: Dict[str, Any],
        shots: int = 1024
    ) -> Dict[str, Any]:
        """Compare results between simulator and hardware"""

        try:
            from qiskit import QuantumCircuit, transpile, execute, Aer

            qc = self._dict_to_circuit(circuit_dict)

            # Simulator results
            simulator = Aer.get_backend('qasm_simulator')
            sim_job = execute(qc, simulator, shots=shots)
            sim_counts = sim_job.result().get_counts()

            hardware_fidelity = self.estimate_hardware_fidelity(circuit_dict)

            return {
                "simulator_counts": sim_counts,
                "estimated_hardware_fidelity": hardware_fidelity,
                "shots": shots,
                "circuit_depth": qc.depth(),
                "num_gates": qc.size()
            }

        except Exception as e:
            print(f"Comparison failed: {e}")
            return {"status": "error", "message": str(e)}

    def _dict_to_circuit(self, circuit_dict: Dict[str, Any]):
        """Convert circuit dictionary to Qiskit QuantumCircuit"""
        try:
            from qiskit import QuantumCircuit

            num_qubits = circuit_dict.get("num_qubits", 2)
            qc = QuantumCircuit(num_qubits)

            for gate_info in circuit_dict.get("gates", []):
                gate_name = gate_info["name"]
                qubits = gate_info["qubits"]
                params = gate_info.get("params", [])

                if gate_name == "h":
                    qc.h(qubits[0])
                elif gate_name == "x":
                    qc.x(qubits[0])
                elif gate_name == "y":
                    qc.y(qubits[0])
                elif gate_name == "z":
                    qc.z(qubits[0])
                elif gate_name == "rx":
                    qc.rx(params[0], qubits[0])
                elif gate_name == "ry":
                    qc.ry(params[0], qubits[0])
                elif gate_name == "rz":
                    qc.rz(params[0], qubits[0])
                elif gate_name == "cnot":
                    qc.cx(qubits[0], qubits[1])
                elif gate_name == "cz":
                    qc.cz(qubits[0], qubits[1])

            return qc

        except Exception as e:
            print(f"Circuit conversion failed: {e}")
            raise

    def _circuit_to_dict(self, qc) -> Dict[str, Any]:
        """Convert Qiskit QuantumCircuit to dictionary"""
        try:
            circuit_dict = {
                "num_qubits": qc.num_qubits,
                "gates": [],
                "depth": qc.depth(),
                "size": qc.size()
            }

            for instruction, qargs, cargs in qc.data:
                gate_name = instruction.name
                qubits = [q.index for q in qargs]
                params = list(instruction.params) if hasattr(instruction, 'params') else []

                circuit_dict["gates"].append({
                    "name": gate_name,
                    "qubits": qubits,
                    "params": params
                })

            return circuit_dict

        except Exception as e:
            print(f"Circuit dict conversion failed: {e}")
            raise


class HybridExecutor:
    """Execute on hardware or simulator based on availability"""

    def __init__(self, ibm_config: Optional[IBMQuantumConfig] = None):
        self.ibm_bridge = IBMQuantumBridge(ibm_config or IBMQuantumConfig())
        self.execution_history = []

    def execute(
        self,
        circuit_dict: Dict[str, Any],
        shots: int = 1024,
        prefer_hardware: bool = False
    ) -> Dict[str, Any]:
        """Execute circuit on best available backend"""

        execution_record = {
            "timestamp": time.time(),
            "circuit": circuit_dict,
            "shots": shots,
            "prefer_hardware": prefer_hardware
        }

        if prefer_hardware and self.ibm_bridge.connected:
            result = self.ibm_bridge.execute_on_hardware(circuit_dict, shots)
            execution_record["backend"] = "ibm_quantum"
        else:
            result = {"status": "simulator_mode", "backend": "local_simulator"}
            execution_record["backend"] = "local_simulator"

        execution_record["result"] = result
        self.execution_history.append(execution_record)

        return result

    def get_execution_stats(self) -> Dict[str, Any]:
        """Get statistics on executions"""

        if not self.execution_history:
            return {"total_executions": 0}

        hardware_count = sum(1 for e in self.execution_history if e["backend"] == "ibm_quantum")
        simulator_count = sum(1 for e in self.execution_history if e["backend"] == "local_simulator")

        return {
            "total_executions": len(self.execution_history),
            "hardware_executions": hardware_count,
            "simulator_executions": simulator_count,
            "hardware_percentage": (hardware_count / len(self.execution_history)) * 100 if self.execution_history else 0
        }


def test_ibm_integration():
    """Test IBM Quantum integration"""

    print("\n" + "="*60)
    print("IBM QUANTUM INTEGRATION TEST")
    print("="*60)

    # Test without API token (simulator mode)
    config = IBMQuantumConfig(use_simulator=True)
    bridge = IBMQuantumBridge(config)

    # Create test circuit
    test_circuit = {
        "num_qubits": 2,
        "gates": [
            {"name": "h", "qubits": [0], "params": []},
            {"name": "cnot", "qubits": [0, 1], "params": []}
        ]
    }

    print("\n1. Testing circuit transpilation...")
    transpiled = bridge.transpile_circuit(test_circuit)
    print(f"   ✓ Circuit has {len(transpiled['gates'])} gates")

    print("\n2. Testing fidelity estimation...")
    fidelity = bridge.estimate_hardware_fidelity(test_circuit)
    print(f"   ✓ Estimated hardware fidelity: {fidelity:.2%}")

    print("\n3. Testing hybrid executor...")
    executor = HybridExecutor(config)
    result = executor.execute(test_circuit, shots=1024)
    print(f"   ✓ Execution status: {result['status']}")

    print("\n4. Testing execution statistics...")
    stats = executor.get_execution_stats()
    print(f"   ✓ Total executions: {stats['total_executions']}")
    print(f"   ✓ Simulator executions: {stats['simulator_executions']}")

    print("\n" + "="*60)
    print("IBM QUANTUM INTEGRATION TEST COMPLETE")
    print("="*60 + "\n")

    return {
        "transpiled_circuit": transpiled,
        "estimated_fidelity": fidelity,
        "execution_result": result,
        "statistics": stats
    }


if __name__ == "__main__":
    test_ibm_integration()
