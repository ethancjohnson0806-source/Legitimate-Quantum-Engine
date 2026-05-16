"""
Quantum Engine V4: Unified Cross-Paradigm System

This engine integrates three quantum paradigms:
1. Gate-Based Circuits (XEB Benchmarking) - from real IBM hardware
2. Annealing Optimization (Parallel Tempering) - local execution
3. Variational Solver (VQE) - local execution

All three are unified into a single Coherence Index metric.
"""

import numpy as np
import json
import random
from datetime import datetime
from scipy.linalg import expm
from scipy.optimize import minimize
import matplotlib.pyplot as plt

class UnifiedQuantumEngine:
    """
    Cross-paradigm quantum engine that unifies gate-based, annealing, and VQE paradigms.
    """
    
    def __init__(self, num_qubits=5, num_spins=20, seed=42):
        self.num_qubits = num_qubits
        self.num_spins = num_spins
        self.dim = 2 ** num_qubits
        np.random.seed(seed)
        random.seed(seed)
        
        # Quantum gates
        self.H = 1/np.sqrt(2) * np.array([[1, 1], [1, -1]], dtype=complex)
        self.I = np.eye(2, dtype=complex)
        self.X = np.array([[0, 1], [1, 0]], dtype=complex)
        self.Z = np.array([[1, 0], [0, -1]], dtype=complex)
        
        # Execution history
        self.execution_history = []
    
    # ==================== PARADIGM 1: GATE-BASED (XEB) ====================
    
    def rx(self, theta):
        """RX rotation gate."""
        return np.array([[np.cos(theta/2), -1j*np.sin(theta/2)],
                         [-1j*np.sin(theta/2), np.cos(theta/2)]], dtype=complex)
    
    def rz(self, theta):
        """RZ rotation gate."""
        return np.array([[np.exp(-1j*theta/2), 0],
                         [0, np.exp(1j*theta/2)]], dtype=complex)
    
    def apply_gate(self, state, gate, target):
        """Apply a single-qubit gate."""
        state = state.reshape([2] * self.num_qubits)
        state = np.tensordot(gate, state, axes=(1, target))
        state = np.moveaxis(state, 0, target)
        return state.flatten()
    
    def apply_cz(self, state, q1, q2):
        """Apply CZ gate."""
        state = state.reshape([2] * self.num_qubits)
        slices = [slice(None)] * self.num_qubits
        slices[q1] = 1
        slices[q2] = 1
        state[tuple(slices)] *= -1
        return state.flatten()
    
    def calculate_xeb_from_hardware(self, measurement_counts, num_shots=1024):
        """
        Calculate XEB fidelity from real hardware measurement results.
        
        XEB = D * <P(x_i)> - 1
        where D is Hilbert space dimension, P(x_i) is probability of measured bitstring
        """
        # Convert measurement counts to probabilities
        probs = np.array([count / num_shots for count in measurement_counts.values()])
        
        # XEB calculation
        xeb = self.dim * np.sum(probs**2) - 1
        
        return xeb
    
    # ==================== PARADIGM 2: ANNEALING (OPTIMIZATION) ====================
    
    def get_energy(self, spins, h, J):
        """Calculate energy of Ising model."""
        return -np.sum(h * spins) - np.sum(J * np.outer(spins, spins)) / 2
    
    def parallel_tempering(self, steps=500, num_replicas=6):
        """
        Parallel Tempering annealing for optimization.
        Returns the best energy found.
        """
        h = np.random.normal(0, 1.0, self.num_spins)
        J = np.random.normal(0, 1.0, (self.num_spins, self.num_spins))
        J = (J + J.T) / 2
        
        # Initialize replicas at different temperatures
        temperatures = np.logspace(0, 2, num_replicas)  # 1 to 100
        replicas = [np.random.choice([-1, 1], self.num_spins) for _ in range(num_replicas)]
        energies = [self.get_energy(r, h, J) for r in replicas]
        
        best_energy = min(energies)
        
        for step in range(steps):
            # Metropolis step for each replica
            for i, (replica, T) in enumerate(zip(replicas, temperatures)):
                idx = np.random.randint(0, self.num_spins)
                replica_new = replica.copy()
                replica_new[idx] *= -1
                
                E_new = self.get_energy(replica_new, h, J)
                E_old = energies[i]
                
                dE = E_new - E_old
                if dE < 0 or np.random.random() < np.exp(-dE / T):
                    replicas[i] = replica_new
                    energies[i] = E_new
                    best_energy = min(best_energy, E_new)
            
            # Replica exchange
            if step % 10 == 0:
                i = np.random.randint(0, num_replicas - 1)
                if np.random.random() < np.exp(-(1/temperatures[i] - 1/temperatures[i+1]) * (energies[i] - energies[i+1])):
                    replicas[i], replicas[i+1] = replicas[i+1], replicas[i]
                    energies[i], energies[i+1] = energies[i+1], energies[i]
        
        return best_energy
    
    def normalize_energy(self, energy):
        """Normalize energy to [0, 1] scale where lower energy = higher score."""
        # Use sigmoid-like scaling
        return 1.0 / (1.0 + np.exp(energy / 10))
    
    # ==================== PARADIGM 3: VQE (VARIATIONAL SOLVER) ====================
    
    def get_tfim_hamiltonian(self, h_field=0.5):
        """
        Transverse Field Ising Model Hamiltonian.
        H = -J * sum(Z_i Z_{i+1}) - h * sum(X_i)
        """
        H = np.zeros((self.dim, self.dim), dtype=complex)
        
        # ZZ interactions
        for i in range(self.num_qubits - 1):
            # Create Z_i ⊗ Z_{i+1} ⊗ I ⊗ ...
            op = self.Z
            for j in range(1, self.num_qubits):
                if j == i + 1:
                    op = np.kron(op, self.Z)
                else:
                    op = np.kron(op, self.I)
            
            # Add identity before first qubit
            Z_ZZ = np.eye(2**i, dtype=complex)
            for j in range(i, self.num_qubits):
                if j == i:
                    Z_ZZ = np.kron(Z_ZZ, self.Z)
                elif j == i + 1:
                    Z_ZZ = np.kron(Z_ZZ, self.Z)
                else:
                    Z_ZZ = np.kron(Z_ZZ, self.I)
            
            H -= Z_ZZ
        
        # Transverse field
        for i in range(self.num_qubits):
            X_i = np.eye(2**i, dtype=complex)
            X_i = np.kron(X_i, self.X)
            X_i = np.kron(X_i, np.eye(2**(self.num_qubits - i - 1), dtype=complex))
            H -= h_field * X_i
        
        return H
    
    def vqe_ansatz(self, params):
        """Simple VQE ansatz: alternating RY and CZ layers."""
        state = np.zeros(self.dim, dtype=complex)
        state[0] = 1.0
        
        num_layers = len(params) // self.num_qubits
        
        for layer in range(num_layers):
            for q in range(self.num_qubits):
                theta = params[layer * self.num_qubits + q]
                # RY gate
                ry = np.array([[np.cos(theta/2), -np.sin(theta/2)],
                              [np.sin(theta/2), np.cos(theta/2)]], dtype=complex)
                state = self.apply_gate(state, ry, q)
            
            # Entangling layer
            for q in range(self.num_qubits - 1):
                state = self.apply_cz(state, q, q+1)
        
        return state
    
    def vqe_energy(self, params, H):
        """Compute <psi(params) | H | psi(params)>."""
        psi = self.vqe_ansatz(params)
        energy = np.real(np.conj(psi) @ H @ psi)
        return energy
    
    def run_vqe(self):
        """Run VQE to find ground state energy."""
        H = self.get_tfim_hamiltonian()
        
        # Get exact ground state energy for reference
        eigenvalues = np.linalg.eigvalsh(H)
        exact_ground = eigenvalues[0]
        
        # Initial parameters
        initial_params = np.random.uniform(0, 2*np.pi, 2 * self.num_qubits)
        
        # Optimize
        result = minimize(
            lambda p: self.vqe_energy(p, H),
            initial_params,
            method='COBYLA',
            options={'maxiter': 50}
        )
        
        vqe_energy = result.fun
        vqe_error = abs(vqe_energy - exact_ground)
        
        return vqe_error
    
    # ==================== UNIFIED COHERENCE INDEX ====================
    
    def compute_coherence_index(self, xeb_score, annealing_score, vqe_score, 
                               weights=None):
        """
        Compute Unified Coherence Index from all three paradigms.
        
        Coherence = w1 * XEB + w2 * Annealing + w3 * VQE
        
        where:
        - XEB: Benchmarking fidelity (higher is better)
        - Annealing: Optimization quality (higher is better)
        - VQE: Solver accuracy (lower error is better, so 1/(1+error))
        """
        if weights is None:
            weights = {'xeb': 0.4, 'annealing': 0.4, 'vqe': 0.2}
        
        # Normalize VQE error to [0, 1]
        vqe_normalized = 1.0 / (1.0 + vqe_score)
        
        coherence = (weights['xeb'] * xeb_score + 
                    weights['annealing'] * annealing_score + 
                    weights['vqe'] * vqe_normalized)
        
        return coherence
    
    # ==================== UNIFIED EXECUTION ====================
    
    def process_hardware_result(self, hardware_result):
        """
        Process a real hardware execution result and compute full coherence metrics.
        """
        job_id = hardware_result['job_id']
        backend = hardware_result['backend']
        measurement_counts = hardware_result['measurement_counts']
        num_shots = hardware_result['num_shots']
        circuit_depth = hardware_result['circuit_depth']
        
        print(f"\n{'='*80}")
        print(f"UNIFIED QUANTUM ENGINE - Processing Hardware Result")
        print(f"{'='*80}")
        print(f"Job ID: {job_id}")
        print(f"Backend: {backend}")
        print(f"Circuit Depth: {circuit_depth}")
        print(f"Shots: {num_shots}")
        
        # PARADIGM 1: XEB (from hardware)
        print(f"\n[1/3] Gate-Based Paradigm (XEB Benchmarking)...")
        xeb_score = self.calculate_xeb_from_hardware(measurement_counts, num_shots)
        print(f"  XEB Fidelity: {xeb_score:.4f}")
        
        # Normalize XEB to [0, 1] where 1 is perfect
        # Real hardware typically gives negative XEB due to noise
        # We'll use a sigmoid to map to [0, 1]
        xeb_normalized = 1.0 / (1.0 + np.exp(-xeb_score))
        print(f"  XEB Normalized: {xeb_normalized:.4f}")
        
        # PARADIGM 2: Annealing (local)
        print(f"\n[2/3] Annealing Paradigm (Optimization)...")
        best_energy = self.parallel_tempering(steps=300, num_replicas=6)
        annealing_score = self.normalize_energy(best_energy)
        print(f"  Best Energy: {best_energy:.4f}")
        print(f"  Annealing Score: {annealing_score:.4f}")
        
        # PARADIGM 3: VQE (local)
        print(f"\n[3/3] Variational Paradigm (VQE Solver)...")
        vqe_error = self.run_vqe()
        vqe_score = vqe_error
        print(f"  VQE Error: {vqe_error:.4f}")
        
        # UNIFIED COHERENCE INDEX
        print(f"\n{'='*80}")
        print(f"UNIFIED COHERENCE INDEX")
        print(f"{'='*80}")
        
        coherence = self.compute_coherence_index(
            xeb_normalized, 
            annealing_score, 
            vqe_score
        )
        
        print(f"\nComponent Breakdown:")
        print(f"  Gate-Based (XEB):     {xeb_normalized:.4f} (40% weight)")
        print(f"  Annealing:            {annealing_score:.4f} (40% weight)")
        print(f"  Variational (VQE):    {1.0/(1.0+vqe_score):.4f} (20% weight)")
        print(f"\n  UNIFIED COHERENCE:    {coherence:.4f}")
        
        # Store result
        result = {
            'timestamp': datetime.now().isoformat(),
            'job_id': job_id,
            'backend': backend,
            'circuit_depth': circuit_depth,
            'num_shots': num_shots,
            'xeb_raw': xeb_score,
            'xeb_normalized': xeb_normalized,
            'annealing_energy': best_energy,
            'annealing_score': annealing_score,
            'vqe_error': vqe_error,
            'vqe_score': 1.0 / (1.0 + vqe_error),
            'unified_coherence': coherence
        }
        
        self.execution_history.append(result)
        return result
    
    def process_all_hardware_results(self, log_file='quantum_execution_log.json'):
        """Process all hardware results from the execution log."""
        with open(log_file, 'r') as f:
            hardware_results = json.load(f)
        
        all_results = []
        for hw_result in hardware_results:
            result = self.process_hardware_result(hw_result)
            all_results.append(result)
        
        return all_results
    
    def save_results(self, filename='quantum_engine_v4_results.json'):
        """Save all results to file."""
        with open(filename, 'w') as f:
            json.dump(self.execution_history, f, indent=2)
        print(f"\n✅ Results saved to {filename}")
    
    def plot_coherence_analysis(self, filename='quantum_coherence_analysis.png'):
        """Plot unified coherence analysis."""
        if not self.execution_history:
            print("No execution history to plot.")
            return
        
        results = self.execution_history
        job_ids = [r['job_id'][:8] for r in results]
        xeb = [r['xeb_normalized'] for r in results]
        annealing = [r['annealing_score'] for r in results]
        vqe = [r['vqe_score'] for r in results]
        coherence = [r['unified_coherence'] for r in results]
        
        fig, axs = plt.subplots(2, 2, figsize=(14, 10))
        fig.suptitle('Unified Quantum Engine: Cross-Paradigm Analysis', fontsize=16, fontweight='bold')
        
        # XEB
        axs[0, 0].bar(range(len(job_ids)), xeb, color='#2E86AB', alpha=0.8)
        axs[0, 0].set_title('Gate-Based Paradigm (XEB)', fontweight='bold')
        axs[0, 0].set_ylabel('Normalized Fidelity')
        axs[0, 0].set_xticks(range(len(job_ids)))
        axs[0, 0].set_xticklabels(job_ids, rotation=45)
        axs[0, 0].set_ylim([0, 1])
        axs[0, 0].grid(axis='y', alpha=0.3)
        
        # Annealing
        axs[0, 1].bar(range(len(job_ids)), annealing, color='#A23B72', alpha=0.8)
        axs[0, 1].set_title('Annealing Paradigm (Optimization)', fontweight='bold')
        axs[0, 1].set_ylabel('Optimization Score')
        axs[0, 1].set_xticks(range(len(job_ids)))
        axs[0, 1].set_xticklabels(job_ids, rotation=45)
        axs[0, 1].set_ylim([0, 1])
        axs[0, 1].grid(axis='y', alpha=0.3)
        
        # VQE
        axs[1, 0].bar(range(len(job_ids)), vqe, color='#F18F01', alpha=0.8)
        axs[1, 0].set_title('Variational Paradigm (VQE)', fontweight='bold')
        axs[1, 0].set_ylabel('Solver Accuracy')
        axs[1, 0].set_xticks(range(len(job_ids)))
        axs[1, 0].set_xticklabels(job_ids, rotation=45)
        axs[1, 0].set_ylim([0, 1])
        axs[1, 0].grid(axis='y', alpha=0.3)
        
        # Unified Coherence
        colors = ['#2E86AB' if c > 0.5 else '#C1121F' for c in coherence]
        axs[1, 1].bar(range(len(job_ids)), coherence, color=colors, alpha=0.8)
        axs[1, 1].set_title('Unified Coherence Index', fontweight='bold')
        axs[1, 1].set_ylabel('Coherence Score')
        axs[1, 1].set_xticks(range(len(job_ids)))
        axs[1, 1].set_xticklabels(job_ids, rotation=45)
        axs[1, 1].set_ylim([0, 1])
        axs[1, 1].axhline(y=0.5, color='gray', linestyle='--', alpha=0.5, label='Threshold')
        axs[1, 1].grid(axis='y', alpha=0.3)
        axs[1, 1].legend()
        
        plt.tight_layout()
        plt.savefig(filename, dpi=150)
        print(f"✅ Plot saved to {filename}")
        plt.close()


if __name__ == "__main__":
    print("🚀 UNIFIED QUANTUM ENGINE V4")
    print("Cross-Paradigm Integration: Gate-Based + Annealing + VQE")
    
    engine = UnifiedQuantumEngine(num_qubits=5, num_spins=20)
    
    # Process all hardware results
    results = engine.process_all_hardware_results()
    
    # Save results
    engine.save_results()
    
    # Plot analysis
    engine.plot_coherence_analysis()
    
    # Summary
    print(f"\n{'='*80}")
    print("SUMMARY")
    print(f"{'='*80}")
    avg_coherence = np.mean([r['unified_coherence'] for r in results])
    print(f"Average Unified Coherence: {avg_coherence:.4f}")
    print(f"Processed {len(results)} hardware results")
    print(f"\n✅ Quantum Engine V4 Complete")
