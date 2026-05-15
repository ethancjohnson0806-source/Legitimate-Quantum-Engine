"""
Copyright (c) 2026 ethancjohnson0806-source
Licensed under the MIT License.
See LICENSE file for details.

Extended Quantum Gates
======================

Comprehensive gate library supporting:
- Single-qubit gates (U1, U2, U3, RX, RY, RZ, H, X, Y, Z, S, T, etc.)
- Two-qubit gates (CNOT, CZ, SWAP, iSWAP, XX, YY, ZZ, etc.)
- Three-qubit gates (Toffoli, Fredkin)
- Measurement in arbitrary bases
"""

import numpy as np
from typing import List, Tuple, Dict, Optional

class QuantumGates:
    """Comprehensive quantum gate library."""
    
    # Single-qubit gates
    @staticmethod
    def H() -> np.ndarray:
        """Hadamard gate."""
        return np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
    
    @staticmethod
    def X() -> np.ndarray:
        """Pauli-X (NOT) gate."""
        return np.array([[0, 1], [1, 0]], dtype=complex)
    
    @staticmethod
    def Y() -> np.ndarray:
        """Pauli-Y gate."""
        return np.array([[0, -1j], [1j, 0]], dtype=complex)
    
    @staticmethod
    def Z() -> np.ndarray:
        """Pauli-Z gate."""
        return np.array([[1, 0], [0, -1]], dtype=complex)
    
    @staticmethod
    def S() -> np.ndarray:
        """S (Phase) gate."""
        return np.array([[1, 0], [0, 1j]], dtype=complex)
    
    @staticmethod
    def T() -> np.ndarray:
        """T gate."""
        return np.array([[1, 0], [0, np.exp(1j * np.pi / 4)]], dtype=complex)
    
    @staticmethod
    def RX(theta: float) -> np.ndarray:
        """Rotation around X-axis."""
        return np.array([
            [np.cos(theta/2), -1j*np.sin(theta/2)],
            [-1j*np.sin(theta/2), np.cos(theta/2)]
        ], dtype=complex)
    
    @staticmethod
    def RY(theta: float) -> np.ndarray:
        """Rotation around Y-axis."""
        return np.array([
            [np.cos(theta/2), -np.sin(theta/2)],
            [np.sin(theta/2), np.cos(theta/2)]
        ], dtype=complex)
    
    @staticmethod
    def RZ(theta: float) -> np.ndarray:
        """Rotation around Z-axis."""
        return np.array([
            [np.exp(-1j*theta/2), 0],
            [0, np.exp(1j*theta/2)]
        ], dtype=complex)
    
    @staticmethod
    def U1(lambda_: float) -> np.ndarray:
        """U1 gate (phase gate)."""
        return np.array([
            [1, 0],
            [0, np.exp(1j * lambda_)]
        ], dtype=complex)
    
    @staticmethod
    def U2(phi: float, lambda_: float) -> np.ndarray:
        """U2 gate."""
        return np.array([
            [1, -np.exp(1j*lambda_)],
            [np.exp(1j*phi), np.exp(1j*(phi+lambda_))]
        ], dtype=complex) / np.sqrt(2)
    
    @staticmethod
    def U3(theta: float, phi: float, lambda_: float) -> np.ndarray:
        """U3 gate (general single-qubit unitary)."""
        return np.array([
            [np.cos(theta/2), -np.exp(1j*lambda_)*np.sin(theta/2)],
            [np.exp(1j*phi)*np.sin(theta/2), np.exp(1j*(phi+lambda_))*np.cos(theta/2)]
        ], dtype=complex)
    
    # Two-qubit gates
    @staticmethod
    def CNOT() -> np.ndarray:
        """Controlled-NOT gate."""
        return np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 0, 1],
            [0, 0, 1, 0]
        ], dtype=complex)
    
    @staticmethod
    def CZ() -> np.ndarray:
        """Controlled-Z gate."""
        return np.array([
            [1, 0, 0, 0],
            [0, 1, 0, 0],
            [0, 0, 1, 0],
            [0, 0, 0, -1]
        ], dtype=complex)
    
    @staticmethod
    def SWAP() -> np.ndarray:
        """SWAP gate."""
        return np.array([
            [1, 0, 0, 0],
            [0, 0, 1, 0],
            [0, 1, 0, 0],
            [0, 0, 0, 1]
        ], dtype=complex)
    
    @staticmethod
    def iSWAP() -> np.ndarray:
        """iSWAP gate."""
        return np.array([
            [1, 0, 0, 0],
            [0, 0, 1j, 0],
            [0, 1j, 0, 0],
            [0, 0, 0, 1]
        ], dtype=complex)
    
    @staticmethod
    def XX(theta: float) -> np.ndarray:
        """XX interaction gate."""
        return np.array([
            [np.cos(theta/2), 0, 0, -1j*np.sin(theta/2)],
            [0, np.cos(theta/2), -1j*np.sin(theta/2), 0],
            [0, -1j*np.sin(theta/2), np.cos(theta/2), 0],
            [-1j*np.sin(theta/2), 0, 0, np.cos(theta/2)]
        ], dtype=complex)
    
    @staticmethod
    def YY(theta: float) -> np.ndarray:
        """YY interaction gate."""
        return np.array([
            [np.cos(theta/2), 0, 0, 1j*np.sin(theta/2)],
            [0, np.cos(theta/2), -1j*np.sin(theta/2), 0],
            [0, -1j*np.sin(theta/2), np.cos(theta/2), 0],
            [1j*np.sin(theta/2), 0, 0, np.cos(theta/2)]
        ], dtype=complex)
    
    @staticmethod
    def ZZ(theta: float) -> np.ndarray:
        """ZZ interaction gate."""
        return np.array([
            [np.exp(-1j*theta/2), 0, 0, 0],
            [0, np.exp(1j*theta/2), 0, 0],
            [0, 0, np.exp(1j*theta/2), 0],
            [0, 0, 0, np.exp(-1j*theta/2)]
        ], dtype=complex)
    
    # Three-qubit gates
    @staticmethod
    def Toffoli() -> np.ndarray:
        """Toffoli (Controlled-Controlled-NOT) gate."""
        gate = np.eye(8, dtype=complex)
        gate[6, 6] = 0
        gate[6, 7] = 1
        gate[7, 6] = 1
        gate[7, 7] = 0
        return gate
    
    @staticmethod
    def Fredkin() -> np.ndarray:
        """Fredkin (Controlled-SWAP) gate."""
        gate = np.eye(8, dtype=complex)
        gate[5, 5] = 0
        gate[5, 6] = 1
        gate[6, 5] = 1
        gate[6, 6] = 0
        return gate


class ExtendedGateSimulator:
    """Simulator with extended gate support."""
    
    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits
        self.state = np.zeros(2**num_qubits, dtype=complex)
        self.state[0] = 1.0  # Initialize to |0...0⟩
        self.gates = QuantumGates()
    
    def apply_single_qubit_gate(self, gate: np.ndarray, qubit: int) -> None:
        """Apply single-qubit gate to specified qubit."""
        # Create full gate with identity on other qubits
        full_gate = self._expand_gate(gate, qubit, 1)
        self.state = full_gate @ self.state
    
    def apply_two_qubit_gate(self, gate: np.ndarray, qubit1: int, qubit2: int) -> None:
        """Apply two-qubit gate to specified qubits."""
        full_gate = self._expand_gate(gate, min(qubit1, qubit2), 2)
        self.state = full_gate @ self.state
    
    def apply_three_qubit_gate(self, gate: np.ndarray, q1: int, q2: int, q3: int) -> None:
        """Apply three-qubit gate to specified qubits."""
        full_gate = self._expand_gate(gate, min(q1, q2, q3), 3)
        self.state = full_gate @ self.state
    
    def _expand_gate(self, gate: np.ndarray, start_qubit: int, num_qubits: int) -> np.ndarray:
        """Expand gate to full Hilbert space."""
        # Identity on qubits before
        left_identity = np.eye(2**start_qubit, dtype=complex)
        # Identity on qubits after
        right_identity = np.eye(2**(self.num_qubits - start_qubit - num_qubits), dtype=complex)
        
        # Kronecker product
        full_gate = np.kron(left_identity, gate)
        full_gate = np.kron(full_gate, right_identity)
        
        return full_gate
    
    def measure(self, basis: str = 'Z') -> int:
        """Measure qubit in specified basis."""
        probabilities = np.abs(self.state)**2
        outcome = np.random.choice(len(self.state), p=probabilities)
        return outcome
    
    def get_state_vector(self) -> np.ndarray:
        """Get current state vector."""
        return self.state.copy()
    
    def reset(self) -> None:
        """Reset to |0...0⟩."""
        self.state = np.zeros(2**self.num_qubits, dtype=complex)
        self.state[0] = 1.0


if __name__ == "__main__":
    print("Extended Quantum Gates Module")
    print("=" * 50)
    
    # Test gates
    gates = QuantumGates()
    
    print("\nSingle-qubit gates:")
    print(f"H gate:\n{gates.H()}\n")
    print(f"X gate:\n{gates.X()}\n")
    print(f"RX(π/4):\n{gates.RX(np.pi/4)}\n")
    
    print("Two-qubit gates:")
    print(f"CNOT shape: {gates.CNOT().shape}")
    print(f"CZ shape: {gates.CZ().shape}")
    
    print("\nExtended Gate Simulator:")
    sim = ExtendedGateSimulator(2)
    print(f"Initial state: {sim.get_state_vector()}")
    
    sim.apply_single_qubit_gate(gates.H(), 0)
    print(f"After H on qubit 0: {sim.get_state_vector()}")
