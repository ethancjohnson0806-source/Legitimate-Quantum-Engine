"""
Copyright (c) 2026 ethancjohnson0806-source
Licensed under the MIT License.
See LICENSE file for details.

Quantum Problem Solvers
=======================

Implementations of:
- VQE (Variational Quantum Eigensolver) - Find ground state energies
- QAOA (Quantum Approximate Optimization Algorithm) - Solve optimization problems
- Grover's Algorithm - Database search
"""

import numpy as np
from typing import List, Tuple, Dict, Callable, Optional
from .quantum_extended_gates import QuantumGates, ExtendedGateSimulator

class VQE:
    """Variational Quantum Eigensolver."""
    
    def __init__(self, num_qubits: int, hamiltonian: np.ndarray):
        """
        Initialize VQE.
        
        Args:
            num_qubits: Number of qubits
            hamiltonian: Hamiltonian matrix (2^n x 2^n)
        """
        self.num_qubits = num_qubits
        self.hamiltonian = hamiltonian
        self.gates = QuantumGates()
        self.iteration = 0
        self.history = []
    
    def ansatz(self, params: List[float], num_qubits: int) -> np.ndarray:
        """
        Simple ansatz: alternating RY and CNOT layers.
        
        Args:
            params: Rotation parameters
            num_qubits: Number of qubits
            
        Returns:
            State vector
        """
        state = np.zeros(2**num_qubits, dtype=complex)
        state[0] = 1.0
        
        # Apply RY rotations
        for i, param in enumerate(params[:num_qubits]):
            ry_gate = self.gates.RY(param)
            # Apply to qubit i
            left = np.eye(2**i, dtype=complex)
            right = np.eye(2**(num_qubits-i-1), dtype=complex)
            full_gate = np.kron(np.kron(left, ry_gate), right)
            state = full_gate @ state
        
        # Apply CNOT ladder
        for i in range(num_qubits - 1):
            cnot = self.gates.CNOT()
            left = np.eye(2**i, dtype=complex)
            right = np.eye(2**(num_qubits-i-2), dtype=complex)
            full_gate = np.kron(np.kron(left, cnot), right)
            state = full_gate @ state
        
        return state
    
    def compute_energy(self, params: List[float]) -> float:
        """Compute expectation value of Hamiltonian."""
        state = self.ansatz(params, self.num_qubits)
        energy = np.real(np.conj(state) @ self.hamiltonian @ state)
        return energy
    
    def optimize(self, initial_params: Optional[List[float]] = None, 
                 learning_rate: float = 0.01, iterations: int = 100) -> Dict:
        """
        Optimize parameters using gradient descent.
        
        Args:
            initial_params: Starting parameters
            learning_rate: Learning rate for gradient descent
            iterations: Number of iterations
            
        Returns:
            Optimization results
        """
        if initial_params is None:
            params = np.random.randn(self.num_qubits) * 0.1
        else:
            params = np.array(initial_params)
        
        best_energy = float('inf')
        best_params = params.copy()
        
        for it in range(iterations):
            # Compute gradient numerically
            gradient = np.zeros_like(params)
            delta = 1e-5
            
            for i in range(len(params)):
                params_plus = params.copy()
                params_plus[i] += delta
                energy_plus = self.compute_energy(params_plus)
                
                params_minus = params.copy()
                params_minus[i] -= delta
                energy_minus = self.compute_energy(params_minus)
                
                gradient[i] = (energy_plus - energy_minus) / (2 * delta)
            
            # Update parameters
            params -= learning_rate * gradient
            
            # Track best
            energy = self.compute_energy(params)
            self.history.append(energy)
            
            if energy < best_energy:
                best_energy = energy
                best_params = params.copy()
            
            if it % 10 == 0:
                print(f"VQE Iteration {it}: Energy = {energy:.6f}")
        
        return {
            'optimal_params': best_params,
            'optimal_energy': best_energy,
            'history': self.history,
            'iterations': iterations
        }


class QAOA:
    """Quantum Approximate Optimization Algorithm."""
    
    def __init__(self, num_qubits: int, cost_hamiltonian: np.ndarray):
        """
        Initialize QAOA.
        
        Args:
            num_qubits: Number of qubits
            cost_hamiltonian: Cost Hamiltonian (what we're optimizing)
        """
        self.num_qubits = num_qubits
        self.cost_hamiltonian = cost_hamiltonian
        self.gates = QuantumGates()
        self.history = []
    
    def qaoa_circuit(self, gamma: float, beta: float) -> np.ndarray:
        """
        QAOA circuit with one layer.
        
        Args:
            gamma: Cost Hamiltonian parameter
            beta: Mixer Hamiltonian parameter
            
        Returns:
            Final state
        """
        # Initialize to superposition
        state = np.ones(2**self.num_qubits, dtype=complex) / np.sqrt(2**self.num_qubits)
        
        # Cost Hamiltonian evolution (approximated)
        cost_exp = np.linalg.matrix_power(self.cost_hamiltonian, 1)
        state = np.exp(-1j * gamma * cost_exp) @ state
        
        # Mixer Hamiltonian (X on all qubits)
        for i in range(self.num_qubits):
            x_gate = self.gates.X()
            left = np.eye(2**i, dtype=complex)
            right = np.eye(2**(self.num_qubits-i-1), dtype=complex)
            full_gate = np.kron(np.kron(left, x_gate), right)
            state = np.exp(-1j * beta * full_gate) @ state
        
        return state
    
    def objective(self, params: Tuple[float, float]) -> float:
        """Compute objective (expectation of cost Hamiltonian)."""
        gamma, beta = params
        state = self.qaoa_circuit(gamma, beta)
        cost = np.real(np.conj(state) @ self.cost_hamiltonian @ state)
        return cost
    
    def optimize(self, iterations: int = 50) -> Dict:
        """
        Optimize QAOA parameters.
        
        Args:
            iterations: Number of optimization iterations
            
        Returns:
            Optimization results
        """
        best_cost = float('inf')
        best_params = (0.0, 0.0)
        
        for it in range(iterations):
            # Random search (for simplicity)
            gamma = np.random.uniform(0, 2*np.pi)
            beta = np.random.uniform(0, 2*np.pi)
            
            cost = self.objective((gamma, beta))
            self.history.append(cost)
            
            if cost < best_cost:
                best_cost = cost
                best_params = (gamma, beta)
            
            if it % 10 == 0:
                print(f"QAOA Iteration {it}: Cost = {best_cost:.6f}")
        
        return {
            'optimal_params': best_params,
            'optimal_cost': best_cost,
            'history': self.history,
            'iterations': iterations
        }


class GroverSearch:
    """Grover's Algorithm for database search."""
    
    def __init__(self, num_qubits: int, marked_items: List[int]):
        """
        Initialize Grover's algorithm.
        
        Args:
            num_qubits: Number of qubits (database size = 2^n)
            marked_items: Indices of marked items to find
        """
        self.num_qubits = num_qubits
        self.marked_items = marked_items
        self.gates = QuantumGates()
    
    def oracle(self, state: np.ndarray) -> np.ndarray:
        """
        Oracle: flip phase of marked items.
        
        Args:
            state: Input state
            
        Returns:
            State with marked items phase-flipped
        """
        oracle_matrix = np.eye(2**self.num_qubits, dtype=complex)
        for item in self.marked_items:
            oracle_matrix[item, item] = -1
        
        return oracle_matrix @ state
    
    def diffusion_operator(self, state: np.ndarray) -> np.ndarray:
        """
        Diffusion operator (2|s⟩⟨s| - I).
        
        Args:
            state: Input state
            
        Returns:
            Diffused state
        """
        # Average amplitude
        avg_amplitude = np.mean(state)
        
        # 2|s⟩⟨s| - I
        diffusion = 2 * np.outer(state, np.conj(state)) - np.eye(2**self.num_qubits, dtype=complex)
        
        return diffusion @ state
    
    def search(self, num_iterations: Optional[int] = None) -> Dict:
        """
        Run Grover's algorithm.
        
        Args:
            num_iterations: Number of Grover iterations (default: optimal)
            
        Returns:
            Search results
        """
        # Initialize to superposition
        state = np.ones(2**self.num_qubits, dtype=complex) / np.sqrt(2**self.num_qubits)
        
        # Optimal number of iterations
        if num_iterations is None:
            num_iterations = int(np.pi / 4 * np.sqrt(2**self.num_qubits / len(self.marked_items)))
        
        # Grover iterations
        for it in range(num_iterations):
            state = self.oracle(state)
            state = self.diffusion_operator(state)
            state = state / np.linalg.norm(state)
        
        # Measure
        probabilities = np.abs(state)**2
        
        # Find marked items
        marked_probs = {item: probabilities[item] for item in self.marked_items}
        
        return {
            'marked_probabilities': marked_probs,
            'total_marked_probability': sum(marked_probs.values()),
            'iterations': num_iterations,
            'final_state': state
        }


if __name__ == "__main__":
    print("Quantum Problem Solvers")
    print("=" * 50)
    
    # Test VQE
    print("\n[VQE - Ground State Energy]")
    num_qubits = 2
    # Simple Hamiltonian: Z0 + Z1
    h_matrix = np.array([
        [2, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, 0],
        [0, 0, 0, -2]
    ], dtype=complex)
    
    vqe = VQE(num_qubits, h_matrix)
    result = vqe.optimize(iterations=20)
    print(f"Optimal energy: {result['optimal_energy']:.6f}")
    
    # Test QAOA
    print("\n[QAOA - Optimization]")
    qaoa = QAOA(num_qubits, h_matrix)
    result = qaoa.optimize(iterations=20)
    print(f"Optimal cost: {result['optimal_cost']:.6f}")
    
    # Test Grover's
    print("\n[Grover's Algorithm - Search]")
    grover = GroverSearch(3, [3, 5])  # Search for items 3 and 5 in 8-item database
    result = grover.search()
    print(f"Marked item probabilities: {result['marked_probabilities']}")
    print(f"Total marked probability: {result['total_marked_probability']:.4f}")
