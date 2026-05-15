"""
Copyright (c) 2026 ethancjohnson0806-source
Licensed under the MIT License.
See LICENSE file for details.
"""

Tensor Network Contraction Module
==================================

Represents quantum circuits as tensor networks and finds optimal contraction order.
Can achieve exponential speedup for circuits with tree-like structure.

Key insight: Quantum circuits can be viewed as tensor networks. Contracting
in the right order can reduce complexity from exponential to polynomial.
"""

import numpy as np
from typing import Dict, List, Tuple, Set, Optional
import heapq

class TensorNode:
    """Represents a tensor in the network."""
    
    def __init__(self, node_id: int, tensor: np.ndarray, indices: List[str]):
        """
        Initialize tensor node.
        
        node_id: unique identifier
        tensor: numpy array
        indices: list of index names (e.g., ['a', 'b', 'c'])
        """
        self.id = node_id
        self.tensor = tensor
        self.indices = indices
        self.shape = tensor.shape
    
    def __str__(self):
        return f"TensorNode({self.id}, shape={self.shape}, indices={self.indices})"
    
    def get_dimension(self, index: str) -> int:
        """Get dimension of specific index."""
        if index in self.indices:
            idx = self.indices.index(index)
            return self.shape[idx]
        return None


class TensorNetwork:
    """Represents a quantum circuit as a tensor network."""
    
    def __init__(self):
        self.nodes: Dict[int, TensorNode] = {}
        self.edges: Dict[Tuple[int, int], str] = {}  # (node1, node2) -> index_name
        self.node_counter = 0
    
    def add_node(self, tensor: np.ndarray, indices: List[str]) -> int:
        """Add a tensor node to the network."""
        node_id = self.node_counter
        self.nodes[node_id] = TensorNode(node_id, tensor, indices)
        self.node_counter += 1
        return node_id
    
    def connect_nodes(self, node1: int, node2: int, index1: str, index2: str):
        """Connect two nodes by matching indices."""
        self.edges[(node1, node2)] = (index1, index2)
        self.edges[(node2, node1)] = (index2, index1)
    
    def get_contraction_cost(self, node1: int, node2: int) -> int:
        """Estimate cost of contracting two nodes."""
        n1 = self.nodes[node1]
        n2 = self.nodes[node2]
        
        # Cost is product of all dimensions
        cost = 1
        
        # Contracted indices (free dimensions)
        for dim in n1.shape:
            cost *= dim
        for dim in n2.shape:
            cost *= dim
        
        return cost
    
    def contract_nodes(self, node1: int, node2: int) -> int:
        """Contract two nodes and return new node id."""
        n1 = self.nodes[node1]
        n2 = self.nodes[node2]
        
        # Find common indices
        common_indices = set(n1.indices) & set(n2.indices)
        
        # Create einsum string
        einsum_str = self._create_einsum_string(n1, n2, common_indices)
        
        # Contract
        result_tensor = np.einsum(einsum_str, n1.tensor, n2.tensor)
        
        # Get result indices
        result_indices = [idx for idx in n1.indices if idx not in common_indices] + \
                        [idx for idx in n2.indices if idx not in common_indices]
        
        # Add new node
        new_id = self.add_node(result_tensor, result_indices)
        
        # Update edges
        for (n, other), idx_pair in list(self.edges.items()):
            if n == node1 or n == node2:
                if other not in [node1, node2]:
                    self.edges[(new_id, other)] = idx_pair
                    self.edges[(other, new_id)] = (idx_pair[1], idx_pair[0])
        
        # Remove old nodes
        del self.nodes[node1]
        del self.nodes[node2]
        
        return new_id
    
    def _create_einsum_string(self, n1: TensorNode, n2: TensorNode, common_indices: Set[str]) -> str:
        """Create einsum string for contraction."""
        # Map indices to letters
        index_map = {}
        letter_idx = 0
        
        for idx in n1.indices + n2.indices:
            if idx not in index_map:
                index_map[idx] = chr(ord('a') + letter_idx)
                letter_idx += 1
        
        # Create einsum string
        str1 = ''.join(index_map[idx] for idx in n1.indices)
        str2 = ''.join(index_map[idx] for idx in n2.indices)
        
        # Output indices (non-contracted)
        output_indices = [idx for idx in n1.indices if idx not in common_indices] + \
                        [idx for idx in n2.indices if idx not in common_indices]
        output = ''.join(index_map[idx] for idx in output_indices)
        
        return f"{str1},{str2}->{output}"
    
    def find_optimal_contraction_order(self) -> List[Tuple[int, int]]:
        """Find optimal contraction order using greedy algorithm."""
        contraction_order = []
        remaining_nodes = set(self.nodes.keys())
        
        while len(remaining_nodes) > 1:
            # Find pair with minimum cost
            min_cost = float('inf')
            best_pair = None
            
            for n1 in remaining_nodes:
                for n2 in remaining_nodes:
                    if n1 < n2:
                        cost = self.get_contraction_cost(n1, n2)
                        if cost < min_cost:
                            min_cost = cost
                            best_pair = (n1, n2)
            
            if best_pair:
                contraction_order.append(best_pair)
                # Contract
                new_id = self.contract_nodes(best_pair[0], best_pair[1])
                remaining_nodes.discard(best_pair[0])
                remaining_nodes.discard(best_pair[1])
                remaining_nodes.add(new_id)
        
        return contraction_order
    
    def contract_all(self) -> np.ndarray:
        """Contract entire network."""
        contraction_order = self.find_optimal_contraction_order()
        
        for n1, n2 in contraction_order:
            if n1 in self.nodes and n2 in self.nodes:
                self.contract_nodes(n1, n2)
        
        # Return final result
        final_node = list(self.nodes.values())[0]
        return final_node.tensor


class TensorNetworkSimulator:
    """Quantum simulator using tensor network contraction."""
    
    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits
        
        # Define quantum gates as tensors
        self.H = 1/np.sqrt(2) * np.array([[1, 1], [1, -1]], dtype=complex)
        self.X = np.array([[0, 1], [1, 0]], dtype=complex)
        self.Z = np.array([[1, 0], [0, -1]], dtype=complex)
        self.CNOT = np.array([[1, 0, 0, 0],
                              [0, 1, 0, 0],
                              [0, 0, 0, 1],
                              [0, 0, 1, 0]], dtype=complex).reshape(2, 2, 2, 2)
    
    def simulate(self, gates: List[Tuple], num_shots: int = 1024) -> Dict:
        """Simulate circuit using tensor network."""
        network = TensorNetwork()
        
        # Initialize qubits as |0⟩ states
        qubit_nodes = {}
        for i in range(self.num_qubits):
            zero_state = np.array([1, 0], dtype=complex)
            qubit_nodes[i] = network.add_node(zero_state, [f'q{i}'])
        
        # Apply gates
        for gate_type, qubits in gates:
            if gate_type == 'H':
                q = qubits[0]
                old_node = qubit_nodes[q]
                new_node = network.add_node(self.H, [f'in_{q}', f'out_{q}'])
                # Connect
                network.connect_nodes(old_node, new_node, f'q{q}', f'in_{q}')
                qubit_nodes[q] = new_node
            
            elif gate_type == 'X':
                q = qubits[0]
                old_node = qubit_nodes[q]
                new_node = network.add_node(self.X, [f'in_{q}', f'out_{q}'])
                network.connect_nodes(old_node, new_node, f'q{q}', f'in_{q}')
                qubit_nodes[q] = new_node
            
            elif gate_type == 'Z':
                q = qubits[0]
                old_node = qubit_nodes[q]
                new_node = network.add_node(self.Z, [f'in_{q}', f'out_{q}'])
                network.connect_nodes(old_node, new_node, f'q{q}', f'in_{q}')
                qubit_nodes[q] = new_node
            
            elif gate_type == 'CNOT':
                q1, q2 = qubits[0], qubits[1]
                old_node1 = qubit_nodes[q1]
                old_node2 = qubit_nodes[q2]
                new_node = network.add_node(self.CNOT, [f'in1_{q1}', f'in2_{q2}', f'out1_{q1}', f'out2_{q2}'])
                network.connect_nodes(old_node1, new_node, f'q{q1}', f'in1_{q1}')
                network.connect_nodes(old_node2, new_node, f'q{q2}', f'in2_{q2}')
                qubit_nodes[q1] = new_node
                qubit_nodes[q2] = new_node
        
        # Contract network
        result = network.contract_all()
        
        # Get probabilities
        probabilities = np.abs(result) ** 2
        probabilities = probabilities.flatten()
        probabilities = probabilities / np.sum(probabilities)
        
        # Sample
        outcomes = np.random.choice(len(probabilities), size=num_shots, p=probabilities)
        
        # Count outcomes
        counts = {}
        for outcome in outcomes:
            bitstring = format(outcome, f'0{self.num_qubits}b')
            counts[bitstring] = counts.get(bitstring, 0) + 1
        
        return {
            'method': 'tensor_network',
            'measurement_counts': counts,
            'network_nodes': len(network.nodes),
            'network_edges': len(network.edges)
        }


def main():
    """Test tensor network simulator."""
    print("="*80)
    print("TENSOR NETWORK SIMULATOR TEST")
    print("="*80)
    
    # Test 1: Simple circuit
    print("\n[Test 1] Simple Circuit (H + X)")
    sim = TensorNetworkSimulator(num_qubits=3)
    circuit1 = [
        ('H', [0]),
        ('X', [1]),
        ('Z', [2])
    ]
    result1 = sim.simulate(circuit1)
    print(f"  Method: {result1['method']}")
    print(f"  Network nodes: {result1['network_nodes']}")
    print(f"  Network edges: {result1['network_edges']}")
    print(f"  Measurement outcomes: {len(result1['measurement_counts'])}")
    
    # Test 2: Entangling circuit
    print("\n[Test 2] Entangling Circuit (CNOT)")
    circuit2 = [
        ('H', [0]),
        ('CNOT', [0, 1]),
        ('CNOT', [1, 2])
    ]
    result2 = sim.simulate(circuit2)
    print(f"  Network nodes: {result2['network_nodes']}")
    print(f"  Network edges: {result2['network_edges']}")
    print(f"  Measurement outcomes: {len(result2['measurement_counts'])}")
    
    print("\n✅ Tensor Network Simulator Test Complete")


if __name__ == "__main__":
    main()
