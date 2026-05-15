"""
Copyright (c) 2026 ethancjohnson0806-source
Licensed under the MIT License.
See LICENSE file for details.
"""

Sparse State Representation Module
===================================

Instead of storing full 2^n state vector, only store non-zero amplitudes.
This dramatically reduces memory for sparse states.

Key insight: Many quantum states are sparse (most amplitudes are zero or negligible).
"""

import numpy as np
from typing import Dict, Tuple, Optional
from collections import defaultdict

class SparseQuantumState:
    """Represents quantum state using sparse dictionary format."""
    
    def __init__(self, num_qubits: int, amplitude_threshold: float = 1e-10):
        """
        Initialize sparse state.
        
        amplitude_threshold: amplitudes below this are treated as zero
        """
        self.num_qubits = num_qubits
        self.dim = 2 ** num_qubits
        self.amplitude_threshold = amplitude_threshold
        
        # Sparse representation: {basis_state_index: amplitude}
        self.amplitudes = {0: 1.0 + 0j}  # Initialize to |0...0⟩
        
        self.compression_stats = {
            'original_size': self.dim,
            'compressed_size': 1,
            'compression_ratio': 1.0 / self.dim
        }
    
    def __len__(self):
        """Return number of non-zero amplitudes."""
        return len(self.amplitudes)
    
    def __str__(self):
        return f"SparseQuantumState({self.num_qubits} qubits, {len(self)} non-zero amplitudes)"
    
    def get_amplitude(self, basis_state: int) -> complex:
        """Get amplitude for basis state."""
        return self.amplitudes.get(basis_state, 0.0 + 0j)
    
    def set_amplitude(self, basis_state: int, amplitude: complex):
        """Set amplitude for basis state."""
        if abs(amplitude) < self.amplitude_threshold:
            # Remove if below threshold
            self.amplitudes.pop(basis_state, None)
        else:
            self.amplitudes[basis_state] = amplitude
    
    def apply_single_qubit_gate(self, gate_matrix: np.ndarray, target_qubit: int) -> 'SparseQuantumState':
        """Apply single-qubit gate to sparse state."""
        new_state = SparseQuantumState(self.num_qubits, self.amplitude_threshold)
        new_state.amplitudes = {}
        
        for basis_state, amplitude in self.amplitudes.items():
            # Extract target qubit value
            qubit_value = (basis_state >> target_qubit) & 1
            
            # Apply gate
            for out_val in [0, 1]:
                gate_element = gate_matrix[out_val, qubit_value]
                if abs(gate_element) > self.amplitude_threshold:
                    # Construct new basis state
                    new_basis = basis_state & ~(1 << target_qubit)  # Clear target bit
                    new_basis |= (out_val << target_qubit)  # Set new value
                    
                    new_amplitude = gate_element * amplitude
                    if new_basis in new_state.amplitudes:
                        new_state.amplitudes[new_basis] += new_amplitude
                    else:
                        new_state.amplitudes[new_basis] = new_amplitude
        
        # Clean up small amplitudes
        new_state.amplitudes = {
            k: v for k, v in new_state.amplitudes.items()
            if abs(v) > self.amplitude_threshold
        }
        
        return new_state
    
    def apply_two_qubit_gate(self, gate_matrix: np.ndarray, qubit1: int, qubit2: int) -> 'SparseQuantumState':
        """Apply two-qubit gate to sparse state."""
        new_state = SparseQuantumState(self.num_qubits, self.amplitude_threshold)
        new_state.amplitudes = {}
        
        for basis_state, amplitude in self.amplitudes.items():
            # Extract qubit values
            val1 = (basis_state >> qubit1) & 1
            val2 = (basis_state >> qubit2) & 1
            input_state = val1 * 2 + val2
            
            # Apply gate
            for out_state in range(4):
                gate_element = gate_matrix[out_state, input_state]
                if abs(gate_element) > self.amplitude_threshold:
                    out_val1 = (out_state >> 1) & 1
                    out_val2 = out_state & 1
                    
                    # Construct new basis state
                    new_basis = basis_state & ~(1 << qubit1) & ~(1 << qubit2)
                    new_basis |= (out_val1 << qubit1)
                    new_basis |= (out_val2 << qubit2)
                    
                    new_amplitude = gate_element * amplitude
                    if new_basis in new_state.amplitudes:
                        new_state.amplitudes[new_basis] += new_amplitude
                    else:
                        new_state.amplitudes[new_basis] = new_amplitude
        
        # Clean up
        new_state.amplitudes = {
            k: v for k, v in new_state.amplitudes.items()
            if abs(v) > self.amplitude_threshold
        }
        
        return new_state
    
    def measure(self, num_shots: int = 1024) -> Dict[str, int]:
        """Measure all qubits."""
        # Compute probabilities
        probabilities = {}
        total_prob = 0.0
        
        for basis_state, amplitude in self.amplitudes.items():
            prob = abs(amplitude) ** 2
            probabilities[basis_state] = prob
            total_prob += prob
        
        # Normalize (should be ~1.0)
        if total_prob > 0:
            probabilities = {k: v / total_prob for k, v in probabilities.items()}
        
        # Sample
        basis_states = list(probabilities.keys())
        probs = list(probabilities.values())
        
        outcomes = np.random.choice(basis_states, size=num_shots, p=probs)
        
        # Convert to bitstrings
        counts = {}
        for outcome in outcomes:
            bitstring = format(outcome, f'0{self.num_qubits}b')
            counts[bitstring] = counts.get(bitstring, 0) + 1
        
        return counts
    
    def get_compression_ratio(self) -> float:
        """Get compression ratio vs full state vector."""
        return len(self.amplitudes) / self.dim
    
    def get_memory_savings(self) -> Dict:
        """Calculate memory savings."""
        full_size_bytes = self.dim * 16  # 16 bytes per complex number
        sparse_size_bytes = len(self.amplitudes) * (8 + 16)  # 8 bytes for index, 16 for amplitude
        
        return {
            'full_state_bytes': full_size_bytes,
            'sparse_state_bytes': sparse_size_bytes,
            'savings_ratio': full_size_bytes / sparse_size_bytes,
            'savings_percent': (1 - sparse_size_bytes / full_size_bytes) * 100
        }


class SparseStateSimulator:
    """Quantum simulator using sparse state representation."""
    
    def __init__(self, num_qubits: int, amplitude_threshold: float = 1e-10):
        self.num_qubits = num_qubits
        self.amplitude_threshold = amplitude_threshold
        self.state = SparseQuantumState(num_qubits, amplitude_threshold)
        
        # Define quantum gates
        self.H = 1/np.sqrt(2) * np.array([[1, 1], [1, -1]], dtype=complex)
        self.X = np.array([[0, 1], [1, 0]], dtype=complex)
        self.Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
        self.Z = np.array([[1, 0], [0, -1]], dtype=complex)
        self.S = np.array([[1, 0], [0, 1j]], dtype=complex)
        self.T = np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex)
        
        # Two-qubit gates
        self.CNOT = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 0, 1],
            [0, 0, 1, 0]
        ], dtype=complex)
        
        self.CZ = np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, -1]
        ], dtype=complex)
    
    def apply_gate(self, gate_type: str, qubits: list) -> None:
        """Apply a gate to the current state."""
        if gate_type == 'H':
            self.state = self.state.apply_single_qubit_gate(self.H, qubits[0])
        elif gate_type == 'X':
            self.state = self.state.apply_single_qubit_gate(self.X, qubits[0])
        elif gate_type == 'Y':
            self.state = self.state.apply_single_qubit_gate(self.Y, qubits[0])
        elif gate_type == 'Z':
            self.state = self.state.apply_single_qubit_gate(self.Z, qubits[0])
        elif gate_type == 'S':
            self.state = self.state.apply_single_qubit_gate(self.S, qubits[0])
        elif gate_type == 'T':
            self.state = self.state.apply_single_qubit_gate(self.T, qubits[0])
        elif gate_type == 'CNOT':
            self.state = self.state.apply_two_qubit_gate(self.CNOT, qubits[0], qubits[1])
        elif gate_type == 'CZ':
            self.state = self.state.apply_two_qubit_gate(self.CZ, qubits[0], qubits[1])
    
    def simulate(self, gates: list, num_shots: int = 1024) -> Dict:
        """Simulate circuit with sparse state."""
        # Reset state
        self.state = SparseQuantumState(self.num_qubits, self.amplitude_threshold)
        
        # Track compression
        max_compression = 1.0
        
        # Apply gates
        for gate_type, qubits in gates:
            self.apply_gate(gate_type, qubits)
            compression = self.state.get_compression_ratio()
            max_compression = min(max_compression, compression)
        
        # Measure
        measurement_counts = self.state.measure(num_shots)
        
        # Get memory stats
        memory_stats = self.state.get_memory_savings()
        
        return {
            'method': 'sparse_state',
            'measurement_counts': measurement_counts,
            'non_zero_amplitudes': len(self.state),
            'compression_ratio': self.state.get_compression_ratio(),
            'memory_savings': memory_stats,
            'max_compression': max_compression
        }


def main():
    """Test sparse state simulator."""
    print("="*80)
    print("SPARSE STATE SIMULATOR TEST")
    print("="*80)
    
    # Test 1: Simple circuit
    print("\n[Test 1] Simple Circuit (H gates)")
    sim = SparseStateSimulator(num_qubits=5)
    circuit1 = [
        ('H', [0]),
        ('H', [1]),
        ('H', [2])
    ]
    result1 = sim.simulate(circuit1)
    print(f"  Non-zero amplitudes: {result1['non_zero_amplitudes']}")
    print(f"  Full state size: 2^5 = 32")
    print(f"  Compression ratio: {result1['compression_ratio']:.4f}")
    print(f"  Memory savings: {result1['memory_savings']['savings_percent']:.1f}%")
    print(f"  Speedup factor: {result1['memory_savings']['savings_ratio']:.1f}x")
    
    # Test 2: Entangling circuit
    print("\n[Test 2] Entangling Circuit (H + CNOT)")
    circuit2 = [
        ('H', [0]),
        ('CNOT', [0, 1]),
        ('CNOT', [1, 2]),
        ('H', [3])
    ]
    result2 = sim.simulate(circuit2)
    print(f"  Non-zero amplitudes: {result2['non_zero_amplitudes']}")
    print(f"  Compression ratio: {result2['compression_ratio']:.4f}")
    print(f"  Memory savings: {result2['memory_savings']['savings_percent']:.1f}%")
    print(f"  Speedup factor: {result2['memory_savings']['savings_ratio']:.1f}x")
    
    # Test 3: Large circuit
    print("\n[Test 3] Large Circuit (10 qubits)")
    sim_large = SparseStateSimulator(num_qubits=10)
    circuit3 = [
        ('H', [i]) for i in range(5)
    ] + [
        ('CNOT', [i, i+1]) for i in range(4)
    ]
    result3 = sim_large.simulate(circuit3)
    print(f"  Non-zero amplitudes: {result3['non_zero_amplitudes']}")
    print(f"  Full state size: 2^10 = 1024")
    print(f"  Compression ratio: {result3['compression_ratio']:.6f}")
    print(f"  Memory savings: {result3['memory_savings']['savings_percent']:.1f}%")
    print(f"  Speedup factor: {result3['memory_savings']['savings_ratio']:.1f}x")
    
    print("\n✅ Sparse State Simulator Test Complete")


if __name__ == "__main__":
    main()
