import numpy as np
import random
import time
import matplotlib.pyplot as plt
from scipy.linalg import expm
from scipy.optimize import minimize
import json
from datetime import datetime

# Qiskit imports
try:
    from qiskit import QuantumCircuit, transpile
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
    from qiskit_aer import AerSimulator
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False

class LegitimateQuantumEngineV3:
    """
    Legitimate Quantum Engine V3: 
    Executes real quantum circuits on IBM hardware and computes Porter-Thomas XEB fidelity.
    """
    def __init__(self, num_qubits=5, num_spins=20, seed=42, ibm_token=None):
        self.n = num_qubits
        self.num_spins = num_spins
        self.dim = 2**self.n
        np.random.seed(seed)
        random.seed(seed)
        
        # Gates for local simulation (for ideal state computation)
        self.H = 1/np.sqrt(2) * np.array([[1, 1], [1, -1]], dtype=complex)
        self.I = np.eye(2, dtype=complex)
        self.X = np.array([[0, 1], [1, 0]], dtype=complex)
        self.Z = np.array([[1, 0], [0, -1]], dtype=complex)
        
        # Execution log for tracking real hardware runs
        self.execution_log = []
        
        # Qiskit Service Setup - REAL HARDWARE ONLY
        self.service = None
        self.backend = None
        if QISKIT_AVAILABLE and ibm_token:
            try:
                self.service = QiskitRuntimeService(channel="ibm_quantum_platform", token=ibm_token)
                print("✅ Connected to IBM Quantum Runtime Service")
                
                # Get the least busy real hardware backend (NOT simulator)
                self.backend = self.service.least_busy(operational=True, simulator=False)
                print(f"✅ Using real backend: {self.backend.name}")
            except Exception as e:
                print(f"❌ Failed to connect to IBM Quantum: {e}")
                raise RuntimeError("Cannot proceed without real IBM hardware access")
        else:
            raise RuntimeError("IBM token required for real hardware execution")

    def rx(self, theta):
        return np.array([[np.cos(theta/2), -1j*np.sin(theta/2)],
                         [-1j*np.sin(theta/2), np.cos(theta/2)]], dtype=complex)

    def apply_gate(self, state, gate, target):
        state = state.reshape([2] * self.n)
        state = np.tensordot(gate, state, axes=(1, target))
        state = np.moveaxis(state, 0, target)
        return state.flatten()

    def apply_cz(self, state, q1, q2):
        state = state.reshape([2] * self.n)
        slices = [slice(None)] * self.n
        slices[q1] = 1
        slices[q2] = 1
        state[tuple(slices)] *= -1
        return state.flatten()

    # ====================== CIRCUIT GENERATION ======================
    def generate_random_circuit_data(self, cycles=10):
        """Generate random quantum circuit operations."""
        circuit_ops = []
        for _ in range(cycles):
            layer = []
            for q in range(self.n):
                g_type = random.choice(['H', 'RX', 'RZ'])
                param = random.uniform(0, 2*np.pi) if g_type != 'H' else None
                layer.append((g_type, q, param))
            for q in range(self.n - 1):
                if random.random() < 0.9:
                    layer.append(('CZ', q, q+1))
            circuit_ops.append(layer)
        return circuit_ops

    def build_qiskit_circuit(self, circuit_ops):
        """Build a Qiskit circuit from operations."""
        qc = QuantumCircuit(self.n)
        for layer in circuit_ops:
            for op in layer:
                g_type, q, param = op
                if g_type == 'H': 
                    qc.h(q)
                elif g_type == 'RX': 
                    qc.rx(param, q)
                elif g_type == 'RZ': 
                    qc.rz(param, q)
                elif g_type == 'CZ': 
                    qc.cz(op[1], op[2])
        qc.measure_all()
        return qc

    def compute_ideal_state(self, circuit_ops):
        """Compute the ideal quantum state without measurement."""
        state = np.zeros(self.dim, dtype=complex)
        state[0] = 1.0
        for layer in circuit_ops:
            for op in layer:
                g_type, q, param = op
                if g_type == 'H': 
                    state = self.apply_gate(state, self.H, q)
                elif g_type == 'RX': 
                    state = self.apply_gate(state, self.rx(param), q)
                elif g_type == 'RZ': 
                    rz_gate = np.array([[np.exp(-1j*param/2), 0], [0, np.exp(1j*param/2)]], dtype=complex)
                    state = self.apply_gate(state, rz_gate, q)
                elif g_type == 'CZ': 
                    state = self.apply_cz(state, op[1], op[2])
        return state

    def compute_porter_thomas_fidelity(self, circuit_ops, measurement_counts, num_shots):
        """
        Compute Porter-Thomas fidelity (XEB) from hardware measurements.
        
        XEB = D * <P(x_i)> - 1
        where D is the Hilbert space dimension and <P(x_i)> is the average 
        probability of measured bitstrings.
        """
        # Get ideal probabilities
        ideal_state = self.compute_ideal_state(circuit_ops)
        ideal_probs = np.abs(ideal_state)**2
        
        # Compute average probability of measured outcomes
        measured_probs = []
        for bitstring, count in measurement_counts.items():
            # Convert bitstring to integer index
            idx = int(bitstring, 2)
            prob_measured = count / num_shots
            prob_ideal = ideal_probs[idx]
            measured_probs.append(prob_measured * prob_ideal)
        
        avg_prob = np.mean(measured_probs) if measured_probs else 0
        
        # Porter-Thomas fidelity
        xeb = self.dim * avg_prob - 1
        
        return xeb, ideal_probs, measured_probs

    # ====================== REAL HARDWARE EXECUTION ======================
    def run_hardware_xeb(self, circuit_ops, num_shots=1024):
        """
        Execute circuit on real IBM hardware and compute XEB fidelity.
        
        Returns:
            - xeb: Porter-Thomas fidelity score
            - job_id: IBM job identifier
            - backend_name: Which backend was used
            - timestamp: When the job was submitted
        """
        if not self.service or not self.backend:
            raise RuntimeError("IBM Quantum service not available")
        
        print(f"\n🔥 SUBMITTING TO REAL HARDWARE: {self.backend.name}")
        print(f"   Qubits: {self.n}, Shots: {num_shots}")
        
        # Build circuit
        qc = self.build_qiskit_circuit(circuit_ops)
        
        # Transpile for the backend
        transpiled_qc = transpile(qc, self.backend)
        print(f"   Circuit depth after transpilation: {transpiled_qc.depth()}")
        
        # Execute on real hardware
        try:
            sampler = Sampler(mode=self.backend)
            job = sampler.run([transpiled_qc], shots=num_shots)
            
            print(f"   Job ID: {job.job_id()}")
            print(f"   Status: SUBMITTED - waiting for execution...")
            
            # Wait for results
            result = job.result()
            
            # Extract measurement results
            counts_dict = {}
            for result_data in result:
                # Get the measurement counts from the result
                if hasattr(result_data, 'data'):
                    measurements = result_data.data.meas.get_counts()
                    counts_dict.update(measurements)
            
            print(f"   Status: COMPLETED")
            
            # Compute XEB fidelity
            xeb, ideal_probs, measured_probs = self.compute_porter_thomas_fidelity(
                circuit_ops, counts_dict, num_shots
            )
            
            # Log execution
            execution_record = {
                'timestamp': datetime.now().isoformat(),
                'job_id': job.job_id(),
                'backend': self.backend.name,
                'num_qubits': self.n,
                'num_shots': num_shots,
                'circuit_depth': transpiled_qc.depth(),
                'xeb_fidelity': float(xeb),
                'measurement_counts': counts_dict,
                'status': 'COMPLETED'
            }
            
            self.execution_log.append(execution_record)
            
            return xeb, job.job_id(), self.backend.name, datetime.now().isoformat()
            
        except Exception as e:
            print(f"   ❌ Hardware execution failed: {e}")
            error_record = {
                'timestamp': datetime.now().isoformat(),
                'error': str(e),
                'status': 'FAILED'
            }
            self.execution_log.append(error_record)
            raise

    # ====================== EVOLUTION LOOP ======================
    def evolve(self, iterations=3, num_shots=1024):
        """
        Execute multiple circuits on real hardware and track results.
        """
        print(f"\n🚀 ENGINE V3 ONLINE | Mode: REAL HARDWARE")
        print(f"   Backend: {self.backend.name}")
        print(f"   Executing {iterations} circuits...")
        
        history = []
        for it in range(iterations):
            print(f"\n--- Iteration {it+1}/{iterations} ---")
            
            # Generate random circuit
            ops = self.generate_random_circuit_data(cycles=random.randint(5, 8))
            
            # Execute on real hardware
            xeb, job_id, backend_name, timestamp = self.run_hardware_xeb(ops, num_shots=num_shots)
            
            history.append({
                'iter': it,
                'xeb': xeb,
                'job_id': job_id,
                'backend': backend_name,
                'timestamp': timestamp
            })
            
            print(f"   XEB Fidelity: {xeb:.4f}")
            print(f"   Job ID: {job_id}")
            
            # Small delay between submissions to avoid queue saturation
            if it < iterations - 1:
                time.sleep(2)
        
        return history

    def save_execution_log(self, filename='quantum_execution_log.json'):
        """Save all execution records to file."""
        with open(filename, 'w') as f:
            json.dump(self.execution_log, f, indent=2)
        print(f"\n✅ Execution log saved to {filename}")

if __name__ == "__main__":
    # REAL IBM TOKEN - will execute on actual quantum hardware
    token = "fMDTD4_gG_u6vY1YaZmhNylOT7zmRdwcGZJW8y2vM7E0"
    
    print("🌌 INITIALIZING LEGITIMATE QUANTUM ENGINE V3 - REAL HARDWARE MODE")
    
    engine = LegitimateQuantumEngineV3(num_qubits=5, ibm_token=token)
    
    print("\n🔥 EXECUTING REAL QUANTUM CIRCUITS ON IBM INFRASTRUCTURE...")
    history = engine.evolve(iterations=3, num_shots=1024)
    
    print("\n🏆 REAL HARDWARE EXECUTION COMPLETE!")
    print("\nResults:")
    for h in history:
        print(f"  Iteration {h['iter']+1}: XEB={h['xeb']:.4f} | Job={h['job_id']} | Backend={h['backend']}")
    
    # Save execution log
    engine.save_execution_log()
    
    print("\n✅ All data from real IBM quantum hardware execution.")
