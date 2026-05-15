"""
Copyright (c) 2026 ethancjohnson0806-source
Licensed under the MIT License.
See LICENSE file for details.

Error Mitigation Module
=======================

Techniques to reduce effective noise in quantum simulations:
1. Zero-Noise Extrapolation (ZNE)
2. Readout Error Mitigation (REM)
3. Probabilistic Error Cancellation (PEC)
"""

import numpy as np
from typing import Dict, List, Tuple, Callable
from scipy import linalg

class ZeroNoiseExtrapolation:
    """Zero-Noise Extrapolation - reduce noise by extrapolating to zero noise."""
    
    def __init__(self, noise_level: float = 0.01):
        """Initialize ZNE."""
        self.noise_level = noise_level
        self.calibration_data = []
    
    def apply_noise(self, state: np.ndarray, noise_factor: float) -> np.ndarray:
        """Apply depolarizing noise to quantum state."""
        p = self.noise_level * noise_factor
        d = len(state)
        noisy_state = (1 - p) * state + p * np.eye(d) / d
        return noisy_state
    
    def measure_with_noise(self, state: np.ndarray, noise_factor: float = 1.0) -> np.ndarray:
        """Measure state with noise."""
        noisy_state = self.apply_noise(state, noise_factor)
        probabilities = np.abs(np.diag(noisy_state))
        return probabilities / np.sum(probabilities)
    
    def extrapolate_to_zero_noise(self, measurement_results: List[Tuple[float, np.ndarray]]) -> np.ndarray:
        """Extrapolate measurement results to zero noise."""
        noise_factors = np.array([x[0] for x in measurement_results])
        results = np.array([x[1] for x in measurement_results])
        
        if len(measurement_results) >= 2:
            x1, y1 = noise_factors[0], results[0]
            x2, y2 = noise_factors[1], results[1]
            
            if x2 != x1:
                slope = (y2 - y1) / (x2 - x1)
                zero_noise_result = y1 - slope * x1
                return zero_noise_result
        
        return results[0]
    
    def mitigate(self, noisy_measurement: np.ndarray, num_calibration_points: int = 3) -> np.ndarray:
        """Mitigate noise using ZNE."""
        measurements = []
        for i in range(num_calibration_points):
            noise_factor = i / (num_calibration_points - 1) if num_calibration_points > 1 else 1.0
            result = self.measure_with_noise(np.diag(noisy_measurement), noise_factor)
            measurements.append((noise_factor, result))
        
        mitigated = self.extrapolate_to_zero_noise(measurements)
        mitigated = np.abs(mitigated)
        mitigated = mitigated / np.sum(mitigated)
        
        return mitigated


class ReadoutErrorMitigation:
    """Readout Error Mitigation - correct for measurement errors."""
    
    def __init__(self, num_qubits: int):
        """Initialize REM."""
        self.num_qubits = num_qubits
        self.calibration_matrix = None
        self.inverse_matrix = None
    
    def calibrate(self, error_rates: Dict[int, Tuple[float, float]]) -> None:
        """Calibrate readout errors."""
        dim = 2 ** self.num_qubits
        calib_matrix = np.eye(dim, dtype=float)
        
        for basis_state in range(dim):
            for measured_state in range(dim):
                prob = 1.0
                
                for qubit in range(self.num_qubits):
                    true_bit = (basis_state >> qubit) & 1
                    measured_bit = (measured_state >> qubit) & 1
                    
                    if qubit in error_rates:
                        p01, p10 = error_rates[qubit]
                        
                        if true_bit == 0 and measured_bit == 1:
                            prob *= p01
                        elif true_bit == 1 and measured_bit == 0:
                            prob *= p10
                        elif true_bit == measured_bit:
                            prob *= (1 - (p01 if true_bit == 0 else p10))
                    else:
                        if true_bit == measured_bit:
                            prob *= 1.0
                        else:
                            prob *= 0.0
                
                calib_matrix[measured_state, basis_state] = prob
        
        self.calibration_matrix = calib_matrix
        
        try:
            self.inverse_matrix = np.linalg.inv(calib_matrix)
        except np.linalg.LinAlgError:
            self.inverse_matrix = np.linalg.pinv(calib_matrix)
    
    def mitigate(self, measured_counts: Dict[str, int], total_shots: int) -> Dict[str, int]:
        """Mitigate readout errors."""
        if self.inverse_matrix is None:
            return measured_counts
        
        prob_vector = np.zeros(2 ** self.num_qubits)
        for bitstring, count in measured_counts.items():
            state_idx = int(bitstring, 2)
            prob_vector[state_idx] = count / total_shots
        
        corrected_probs = self.inverse_matrix @ prob_vector
        corrected_probs = np.abs(corrected_probs)
        corrected_probs = corrected_probs / np.sum(corrected_probs)
        
        corrected_counts = {}
        for state_idx in range(len(corrected_probs)):
            bitstring = format(state_idx, f'0{self.num_qubits}b')
            count = int(corrected_probs[state_idx] * total_shots)
            if count > 0:
                corrected_counts[bitstring] = count
        
        return corrected_counts


class ProbabilisticErrorCancellation:
    """Probabilistic Error Cancellation - cancel errors probabilistically."""
    
    def __init__(self, num_qubits: int):
        """Initialize PEC."""
        self.num_qubits = num_qubits
        self.error_channels = {}
    
    def register_error_channel(self, gate_name: str, error_channel: np.ndarray):
        """Register error channel for a gate."""
        self.error_channels[gate_name] = error_channel
    
    def compute_error_inverse(self, error_channel: np.ndarray) -> np.ndarray:
        """Compute pseudo-inverse of error channel."""
        u, s, vh = np.linalg.svd(error_channel)
        s_inv = np.zeros_like(s)
        for i, sv in enumerate(s):
            if sv > 1e-10:
                s_inv[i] = 1.0 / sv
        return vh.T @ np.diag(s_inv) @ u.T
    
    def mitigate_gate_error(self, gate_name: str, num_samples: int = 1000) -> Dict:
        """Mitigate error for a specific gate."""
        if gate_name not in self.error_channels:
            return {'error': f'No error channel registered for {gate_name}'}
        
        error_channel = self.error_channels[gate_name]
        error_inverse = self.compute_error_inverse(error_channel)
        correction_factor = np.linalg.norm(error_inverse) / np.linalg.norm(error_channel)
        
        return {
            'gate': gate_name,
            'correction_factor': correction_factor,
            'error_channel_norm': np.linalg.norm(error_channel),
            'inverse_norm': np.linalg.norm(error_inverse)
        }


class ErrorMitigationPipeline:
    """Combines multiple error mitigation techniques."""
    
    def __init__(self, num_qubits: int, noise_level: float = 0.01):
        self.num_qubits = num_qubits
        self.zne = ZeroNoiseExtrapolation(noise_level)
        self.rem = ReadoutErrorMitigation(num_qubits)
        self.pec = ProbabilisticErrorCancellation(num_qubits)
    
    def calibrate_readout_errors(self, error_rates: Dict[int, Tuple[float, float]]):
        """Calibrate readout error mitigation."""
        self.rem.calibrate(error_rates)
    
    def mitigate(self, measured_counts: Dict[str, int], total_shots: int, 
                 techniques: List[str] = ['zne', 'rem']) -> Dict:
        """Apply error mitigation pipeline."""
        result = measured_counts.copy()
        applied_techniques = []
        
        if 'zne' in techniques:
            prob_vector = np.zeros(2 ** self.num_qubits)
            for bitstring, count in result.items():
                state_idx = int(bitstring, 2)
                prob_vector[state_idx] = count / total_shots
            
            density_matrix = np.diag(prob_vector)
            mitigated_probs = self.zne.mitigate(density_matrix)
            
            result = {}
            for state_idx, prob in enumerate(mitigated_probs):
                bitstring = format(state_idx, f'0{self.num_qubits}b')
                count = int(prob * total_shots)
                if count > 0:
                    result[bitstring] = count
            
            applied_techniques.append('zne')
        
        if 'rem' in techniques and self.rem.inverse_matrix is not None:
            result = self.rem.mitigate(result, total_shots)
            applied_techniques.append('rem')
        
        return {
            'mitigated_counts': result,
            'techniques_applied': applied_techniques,
            'total_shots': total_shots
        }
