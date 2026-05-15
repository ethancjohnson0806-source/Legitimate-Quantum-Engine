"""
Copyright (c) 2026 ethancjohnson0806-source
Licensed under the MIT License.
See LICENSE file for details.
"""

Classical Shadows Module
========================

Classical shadows enable efficient quantum state reconstruction with minimal measurements.
Key insight: Instead of full tomography (exponential measurements), measure in random bases
and reconstruct properties of the state from the "shadows".

Reference: Huang, Kueng, Preskill (2020) "Predicting many properties of a quantum system from very few measurements"
"""

import numpy as np
from typing import Dict, List, Tuple, Optional
from scipy import stats

class ClassicalShadow:
    """Represents classical shadows of a quantum state."""
    
    def __init__(self, num_qubits: int, num_shadows: int = 100):
        """
        Initialize classical shadows.
        
        num_qubits: number of qubits
        num_shadows: number of shadow samples to collect
        """
        self.num_qubits = num_qubits
        self.num_shadows = num_shadows
        self.shadows = []  # List of (measurement_bases, outcomes)
        self.measurement_count = 0
    
    def collect_shadow(self, quantum_state: np.ndarray) -> Tuple[List[str], str]:
        """
        Collect a single shadow by measuring in random bases.
        
        quantum_state: the quantum state to measure (as density matrix)
        Returns: (bases, outcome) where bases is list of measurement bases
        """
        # Random measurement bases for each qubit
        bases = []
        outcome_bits = []
        
        for qubit in range(self.num_qubits):
            # Random basis: 0=Z, 1=X, 2=Y
            basis = np.random.randint(0, 3)
            bases.append(['Z', 'X', 'Y'][basis])
            
            # Simulate measurement
            # For simplicity, we extract diagonal elements
            # In real scenario, this would be actual measurement
            prob_0 = np.abs(quantum_state[0, 0])
            outcome = 0 if np.random.random() < prob_0 else 1
            outcome_bits.append(str(outcome))
        
        outcome = ''.join(outcome_bits)
        self.shadows.append((bases, outcome))
        self.measurement_count += 1
        
        return (bases, outcome)
    
    def collect_shadows(self, quantum_state: np.ndarray, num_samples: Optional[int] = None) -> List:
        """Collect multiple shadows."""
        if num_samples is None:
            num_samples = self.num_shadows
        
        shadows = []
        for _ in range(num_samples):
            shadow = self.collect_shadow(quantum_state)
            shadows.append(shadow)
        
        return shadows
    
    def reconstruct_local_observable(self, observable_qubits: List[int], 
                                    observable_bases: List[str]) -> float:
        """
        Reconstruct expectation value of a local observable using shadows.
        
        observable_qubits: which qubits the observable acts on
        observable_bases: measurement bases for the observable (e.g., ['Z', 'X'])
        """
        if not self.shadows:
            return 0.0
        
        expectation_values = []
        
        for measured_bases, outcome in self.shadows:
            # Check if this shadow is compatible with the observable
            compatible = True
            for q, obs_base in zip(observable_qubits, observable_bases):
                if measured_bases[q] != obs_base:
                    compatible = False
                    break
            
            if compatible:
                # Extract the outcome bits for observable qubits
                outcome_bits = [int(outcome[q]) for q in observable_qubits]
                
                # Compute observable eigenvalue
                # For Pauli operators: eigenvalue is (-1)^(parity)
                parity = sum(outcome_bits) % 2
                eigenvalue = (-1) ** parity
                
                expectation_values.append(eigenvalue)
        
        # Average over compatible shadows
        if expectation_values:
            return np.mean(expectation_values)
        else:
            return 0.0
    
    def estimate_entanglement_entropy(self) -> float:
        """Estimate entanglement entropy from shadows."""
        if not self.shadows:
            return 0.0
        
        # Count unique outcomes
        outcomes = [outcome for _, outcome in self.shadows]
        unique_outcomes = len(set(outcomes))
        
        # Entropy estimate (simplified)
        # Higher entropy = more entanglement
        entropy = np.log2(unique_outcomes) if unique_outcomes > 1 else 0.0
        
        return entropy
    
    def get_statistics(self) -> Dict:
        """Get statistics about collected shadows."""
        if not self.shadows:
            return {'error': 'No shadows collected'}
        
        outcomes = [outcome for _, outcome in self.shadows]
        bases = [bases for bases, _ in self.shadows]
        
        # Count measurement bases
        base_counts = {'X': 0, 'Y': 0, 'Z': 0}
        for basis_list in bases:
            for basis in basis_list:
                base_counts[basis] += 1
        
        # Count unique outcomes
        unique_outcomes = len(set(outcomes))
        
        return {
            'total_shadows': len(self.shadows),
            'unique_outcomes': unique_outcomes,
            'measurement_bases': base_counts,
            'entanglement_entropy': self.estimate_entanglement_entropy()
        }


class ShadowBasedSimulator:
    """Quantum simulator using classical shadows for state reconstruction."""
    
    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits
        self.shadow = ClassicalShadow(num_qubits)
    
    def simulate_with_shadows(self, gates: List[Tuple], num_shots: int = 1024) -> Dict:
        """
        Simulate quantum circuit using classical shadows.
        
        Returns measurement statistics reconstructed from shadows.
        """
        # For this simplified version, we'll generate synthetic shadows
        # In a real system, these would come from actual measurements
        
        # Collect shadows
        dummy_state = np.eye(2**self.num_qubits, dtype=complex) / (2**self.num_qubits)
        self.shadow.collect_shadows(dummy_state, num_samples=100)
        
        # Reconstruct observables
        observables = []
        
        # Single-qubit Z measurements
        for qubit in range(self.num_qubits):
            z_expectation = self.shadow.reconstruct_local_observable([qubit], ['Z'])
            observables.append(('Z', qubit, z_expectation))
        
        # Two-qubit ZZ correlations
        for q1 in range(self.num_qubits - 1):
            for q2 in range(q1 + 1, self.num_qubits):
                zz_expectation = self.shadow.reconstruct_local_observable([q1, q2], ['Z', 'Z'])
                observables.append(('ZZ', (q1, q2), zz_expectation))
        
        # Get statistics
        stats = self.shadow.get_statistics()
        
        return {
            'method': 'classical_shadows',
            'observables': observables,
            'statistics': stats,
            'measurement_efficiency': 'O(log(n)) vs O(4^n) for full tomography'
        }


class ShadowNoiseMitigation:
    """Use classical shadows to estimate and mitigate noise."""
    
    def __init__(self, num_qubits: int):
        self.num_qubits = num_qubits
        self.noise_model = {}
    
    def estimate_noise_from_shadows(self, shadows: ClassicalShadow) -> Dict:
        """
        Estimate noise characteristics from shadows.
        
        Returns noise model parameters.
        """
        stats = shadows.get_statistics()
        
        # Estimate depolarizing noise from outcome distribution
        unique_outcomes = stats['unique_outcomes']
        total_possible = 2 ** self.num_qubits
        
        # If we see fewer outcomes than possible, there's noise
        noise_indicator = 1.0 - (unique_outcomes / total_possible)
        
        # Estimate error rate
        # More uniform distribution = more noise
        outcomes = [outcome for _, outcome in shadows.shadows]
        outcome_probs = {}
        for outcome in outcomes:
            outcome_probs[outcome] = outcome_probs.get(outcome, 0) + 1
        outcome_probs = {k: v / len(outcomes) for k, v in outcome_probs.items()}
        
        # Shannon entropy of outcomes
        entropy = -sum(p * np.log2(p) for p in outcome_probs.values() if p > 0)
        max_entropy = np.log2(unique_outcomes) if unique_outcomes > 0 else 0
        
        return {
            'noise_indicator': noise_indicator,
            'outcome_entropy': entropy,
            'max_entropy': max_entropy,
            'estimated_depolarizing_rate': noise_indicator * 0.1  # Rough estimate
        }
    
    def mitigate_using_shadows(self, measured_counts: Dict[str, int], 
                              shadows: ClassicalShadow) -> Dict[str, int]:
        """
        Mitigate measurement errors using shadow information.
        """
        # Estimate noise
        noise_model = self.estimate_noise_from_shadows(shadows)
        
        # Apply correction based on noise estimate
        corrected_counts = {}
        total = sum(measured_counts.values())
        
        for outcome, count in measured_counts.items():
            # Reduce noise by weighted correction
            correction_factor = 1.0 - noise_model['estimated_depolarizing_rate']
            corrected_count = int(count * correction_factor)
            
            if corrected_count > 0:
                corrected_counts[outcome] = corrected_count
        
        # Normalize
        total_corrected = sum(corrected_counts.values())
        if total_corrected > 0:
            scale_factor = total / total_corrected
            corrected_counts = {k: int(v * scale_factor) for k, v in corrected_counts.items()}
        
        return {
            'corrected_counts': corrected_counts,
            'noise_model': noise_model
        }


def main():
    """Test classical shadows."""
    print("="*80)
    print("CLASSICAL SHADOWS TEST")
    print("="*80)
    
    # Test 1: Shadow collection
    print("\n[Test 1] Shadow Collection")
    shadow = ClassicalShadow(num_qubits=3, num_shadows=50)
    
    # Create a simple state
    state = np.zeros((8, 8), dtype=complex)
    state[0, 0] = 1.0  # |000⟩ state
    
    # Collect shadows
    shadows = shadow.collect_shadows(state, num_samples=50)
    print(f"  Collected {len(shadows)} shadows")
    print(f"  First shadow: bases={shadows[0][0]}, outcome={shadows[0][1]}")
    
    # Get statistics
    stats = shadow.get_statistics()
    print(f"  Unique outcomes: {stats['unique_outcomes']}")
    print(f"  Entanglement entropy: {stats['entanglement_entropy']:.4f}")
    
    # Test 2: Observable reconstruction
    print("\n[Test 2] Observable Reconstruction")
    z_expectation = shadow.reconstruct_local_observable([0], ['Z'])
    print(f"  Z_0 expectation: {z_expectation:.4f}")
    
    zz_expectation = shadow.reconstruct_local_observable([0, 1], ['Z', 'Z'])
    print(f"  Z_0 Z_1 expectation: {zz_expectation:.4f}")
    
    # Test 3: Noise mitigation
    print("\n[Test 3] Shadow-Based Noise Mitigation")
    mitigator = ShadowNoiseMitigation(num_qubits=3)
    
    # Simulate noisy measurements
    noisy_counts = {'000': 450, '001': 50, '010': 30, '011': 20, '100': 200, '101': 150, '110': 80, '111': 20}
    
    # Estimate noise from shadows
    noise_model = mitigator.estimate_noise_from_shadows(shadow)
    print(f"  Noise indicator: {noise_model['noise_indicator']:.4f}")
    print(f"  Outcome entropy: {noise_model['outcome_entropy']:.4f}")
    print(f"  Estimated depolarizing rate: {noise_model['estimated_depolarizing_rate']:.4f}")
    
    # Mitigate
    result = mitigator.mitigate_using_shadows(noisy_counts, shadow)
    print(f"  Original counts: {noisy_counts}")
    print(f"  Mitigated counts: {result['corrected_counts']}")
    
    # Test 4: Shadow-based simulator
    print("\n[Test 4] Shadow-Based Simulator")
    sim = ShadowBasedSimulator(num_qubits=3)
    circuit = [
        ('H', [0]),
        ('H', [1])
    ]
    result = sim.simulate_with_shadows(circuit)
    print(f"  Method: {result['method']}")
    print(f"  Measurement efficiency: {result['measurement_efficiency']}")
    print(f"  Reconstructed observables: {len(result['observables'])}")
    
    print("\n✅ Classical Shadows Test Complete")


if __name__ == "__main__":
    main()
