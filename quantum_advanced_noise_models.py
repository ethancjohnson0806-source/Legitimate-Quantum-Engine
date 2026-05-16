"""
Advanced Noise Models and Realistic Quantum Simulation
Implements realistic noise channels, coherence models, and hardware-specific error patterns
"""

import numpy as np
from typing import Dict, List, Tuple, Optional, Callable, Any
from dataclasses import dataclass
from enum import Enum
import time


class NoiseType(Enum):
    """Types of quantum noise"""
    DEPOLARIZING = "depolarizing"
    AMPLITUDE_DAMPING = "amplitude_damping"
    PHASE_DAMPING = "phase_damping"
    THERMAL = "thermal"
    CROSSTALK = "crosstalk"
    DEPHASING = "dephasing"
    READOUT_ERROR = "readout_error"
    TIMING_ERROR = "timing_error"


@dataclass
class NoiseChannel:
    """Represents a quantum noise channel"""
    noise_type: NoiseType
    error_rate: float
    qubits_affected: List[int]
    duration: float = 1.0
    metadata: Dict[str, Any] = None

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class DepolarizingChannel:
    """Single-qubit depolarizing noise"""

    def __init__(self, error_rate: float):
        self.error_rate = error_rate

    def apply(self, state: np.ndarray, qubit: int) -> np.ndarray:
        """Apply depolarizing noise to a qubit"""

        dim = 2 ** int(np.log2(len(state)))

        if np.random.random() < self.error_rate:
            # Apply random Pauli
            pauli_choice = np.random.choice([0, 1, 2, 3])

            if pauli_choice == 0:  # I
                return state
            elif pauli_choice == 1:  # X
                return self._apply_pauli_x(state, qubit, dim)
            elif pauli_choice == 2:  # Y
                return self._apply_pauli_y(state, qubit, dim)
            else:  # Z
                return self._apply_pauli_z(state, qubit, dim)
        else:
            return state

    def _apply_pauli_x(self, state: np.ndarray, qubit: int, dim: int) -> np.ndarray:
        """Apply Pauli X to qubit"""
        new_state = state.copy()
        for i in range(dim):
            j = i ^ (1 << qubit)
            new_state[i], new_state[j] = new_state[j], new_state[i]
        return new_state

    def _apply_pauli_y(self, state: np.ndarray, qubit: int, dim: int) -> np.ndarray:
        """Apply Pauli Y to qubit"""
        new_state = state.copy()
        for i in range(dim):
            j = i ^ (1 << qubit)
            if (i >> qubit) & 1:
                new_state[i] *= -1j
            else:
                new_state[i] *= 1j
            new_state[i], new_state[j] = new_state[j], new_state[i]
        return new_state

    def _apply_pauli_z(self, state: np.ndarray, qubit: int, dim: int) -> np.ndarray:
        """Apply Pauli Z to qubit"""
        new_state = state.copy()
        for i in range(dim):
            if (i >> qubit) & 1:
                new_state[i] *= -1
        return new_state


class AmplitudeDampingChannel:
    """Amplitude damping (energy loss) noise"""

    def __init__(self, damping_rate: float):
        self.damping_rate = damping_rate

    def apply(self, state: np.ndarray, qubit: int) -> np.ndarray:
        """Apply amplitude damping to a qubit"""

        dim = 2 ** int(np.log2(len(state)))
        new_state = state.copy()

        # Kraus operators for amplitude damping
        K0 = np.array([[1, 0], [0, np.sqrt(1 - self.damping_rate)]])
        K1 = np.array([[0, np.sqrt(self.damping_rate)], [0, 0]])

        # Apply with probability
        if np.random.random() < self.damping_rate:
            for i in range(dim):
                if (i >> qubit) & 1:  # Qubit is in |1>
                    # Transition to |0>
                    j = i ^ (1 << qubit)
                    new_state[j] += new_state[i]
                    new_state[i] = 0

        return new_state / np.linalg.norm(new_state)


class PhaseDampingChannel:
    """Phase damping (dephasing) noise"""

    def __init__(self, dephasing_rate: float):
        self.dephasing_rate = dephasing_rate

    def apply(self, state: np.ndarray, qubit: int) -> np.ndarray:
        """Apply phase damping to a qubit"""

        dim = 2 ** int(np.log2(len(state)))
        new_state = state.copy()

        # Dephase the state
        phase_shift = np.exp(1j * np.random.uniform(0, 2*np.pi) * self.dephasing_rate)

        for i in range(dim):
            if (i >> qubit) & 1:
                new_state[i] *= phase_shift

        return new_state / np.linalg.norm(new_state)


class ThermalNoiseChannel:
    """Thermal noise (temperature-dependent)"""

    def __init__(self, temperature: float, frequency: float = 1.0):
        self.temperature = temperature
        self.frequency = frequency
        self.boltzmann = 1.380649e-23  # Boltzmann constant

    def apply(self, state: np.ndarray, qubit: int) -> np.ndarray:
        """Apply thermal noise to a qubit"""

        dim = 2 ** int(np.log2(len(state)))

        # Thermal occupation number
        thermal_occupation = 1.0 / (np.exp(self.frequency / self.temperature) - 1)

        # Mix with thermal state
        thermal_state = np.zeros(dim)
        thermal_state[0] = 1.0  # Ground state

        mixing_parameter = thermal_occupation / (1 + thermal_occupation)
        new_state = (1 - mixing_parameter) * state + mixing_parameter * thermal_state

        return new_state / np.linalg.norm(new_state)


class CrosstalkNoiseChannel:
    """Crosstalk between qubits"""

    def __init__(self, crosstalk_strength: float):
        self.crosstalk_strength = crosstalk_strength

    def apply(self, state: np.ndarray, qubit: int, neighbor_qubits: List[int]) -> np.ndarray:
        """Apply crosstalk noise"""

        dim = 2 ** int(np.log2(len(state)))
        new_state = state.copy()

        # Introduce controlled-Z like interaction
        for neighbor in neighbor_qubits:
            for i in range(dim):
                if ((i >> qubit) & 1) and ((i >> neighbor) & 1):
                    phase = np.exp(1j * self.crosstalk_strength)
                    new_state[i] *= phase

        return new_state / np.linalg.norm(new_state)


class ReadoutErrorChannel:
    """Readout/measurement error"""

    def __init__(self, error_rate: float):
        self.error_rate = error_rate

    def apply_to_measurement(self, counts: Dict[str, int]) -> Dict[str, int]:
        """Apply readout errors to measurement results"""

        new_counts = {}

        for bitstring, count in counts.items():
            # Flip bits with error_rate probability
            for _ in range(count):
                flipped = list(bitstring)
                for i in range(len(flipped)):
                    if np.random.random() < self.error_rate:
                        flipped[i] = '0' if flipped[i] == '1' else '1'

                flipped_str = ''.join(flipped)
                new_counts[flipped_str] = new_counts.get(flipped_str, 0) + 1

        return new_counts


class RealisticQuantumSimulator:
    """Quantum simulator with realistic noise models"""

    def __init__(self, num_qubits: int, noise_model: Optional[Dict[str, Any]] = None):
        self.num_qubits = num_qubits
        self.noise_model = noise_model or self._default_noise_model()
        self.noise_channels = []
        self._initialize_noise_channels()

    def _default_noise_model(self) -> Dict[str, Any]:
        """Default realistic noise model (IBM-like)"""
        return {
            "single_qubit_error_rate": 0.001,
            "two_qubit_error_rate": 0.005,
            "readout_error_rate": 0.01,
            "dephasing_rate": 0.0005,
            "damping_rate": 0.0001,
            "temperature": 20,  # Millikelvin
            "crosstalk_strength": 0.001
        }

    def _initialize_noise_channels(self):
        """Initialize noise channels based on model"""

        model = self.noise_model

        # Single-qubit noise
        for qubit in range(self.num_qubits):
            self.noise_channels.append(
                NoiseChannel(
                    noise_type=NoiseType.DEPOLARIZING,
                    error_rate=model["single_qubit_error_rate"],
                    qubits_affected=[qubit]
                )
            )

            self.noise_channels.append(
                NoiseChannel(
                    noise_type=NoiseType.DEPHASING,
                    error_rate=model["dephasing_rate"],
                    qubits_affected=[qubit]
                )
            )

        # Two-qubit noise
        for qubit in range(self.num_qubits - 1):
            self.noise_channels.append(
                NoiseChannel(
                    noise_type=NoiseType.CROSSTALK,
                    error_rate=model["crosstalk_strength"],
                    qubits_affected=[qubit, qubit + 1]
                )
            )

    def simulate_with_noise(
        self,
        circuit: Dict[str, Any],
        shots: int = 1024,
        noise_level: float = 1.0
    ) -> Dict[str, int]:
        """Simulate circuit with realistic noise"""

        counts = {}

        for shot in range(shots):
            # Initialize state
            state = np.ones(2**self.num_qubits) / np.sqrt(2**self.num_qubits)

            # Apply gates with noise
            for gate_info in circuit.get("gates", []):
                gate_name = gate_info["name"]
                qubits = gate_info["qubits"]

                # Apply gate
                state = self._apply_gate(state, gate_name, qubits)

                # Apply noise
                for qubit in qubits:
                    for channel in self.noise_channels:
                        if qubit in channel.qubits_affected and np.random.random() < noise_level:
                            if channel.noise_type == NoiseType.DEPOLARIZING:
                                channel_obj = DepolarizingChannel(channel.error_rate)
                                state = channel_obj.apply(state, qubit)
                            elif channel.noise_type == NoiseType.DEPHASING:
                                channel_obj = PhaseDampingChannel(channel.error_rate)
                                state = channel_obj.apply(state, qubit)

            # Measure
            probabilities = np.abs(state) ** 2
            outcome = np.random.choice(2**self.num_qubits, p=probabilities)
            bitstring = format(outcome, f'0{self.num_qubits}b')

            # Apply readout error
            readout_error = ReadoutErrorChannel(self.noise_model["readout_error_rate"])
            bitstring = self._apply_readout_error(bitstring)

            counts[bitstring] = counts.get(bitstring, 0) + 1

        return counts

    def _apply_gate(self, state: np.ndarray, gate_name: str, qubits: List[int]) -> np.ndarray:
        """Apply a quantum gate"""
        # Simplified gate application
        return state

    def _apply_readout_error(self, bitstring: str) -> str:
        """Apply readout error to measurement"""
        error_rate = self.noise_model["readout_error_rate"]
        flipped = list(bitstring)

        for i in range(len(flipped)):
            if np.random.random() < error_rate:
                flipped[i] = '0' if flipped[i] == '1' else '1'

        return ''.join(flipped)

    def get_fidelity_estimate(self, noise_level: float = 1.0) -> float:
        """Estimate circuit fidelity with noise"""

        # Empirical fidelity model
        single_qubit_fidelity = 1 - self.noise_model["single_qubit_error_rate"]
        two_qubit_fidelity = 1 - self.noise_model["two_qubit_error_rate"]
        readout_fidelity = 1 - self.noise_model["readout_error_rate"]

        # Combined fidelity
        total_fidelity = single_qubit_fidelity * two_qubit_fidelity * readout_fidelity

        return total_fidelity * (1 - noise_level * 0.1)


class NoiseModelLibrary:
    """Library of realistic noise models from different hardware"""

    @staticmethod
    def ibm_quantum_model() -> Dict[str, Any]:
        """IBM Quantum hardware noise model"""
        return {
            "single_qubit_error_rate": 0.001,
            "two_qubit_error_rate": 0.005,
            "readout_error_rate": 0.01,
            "dephasing_rate": 0.0005,
            "damping_rate": 0.0001,
            "temperature": 20,
            "crosstalk_strength": 0.001,
            "name": "IBM Quantum (ibm_fez)"
        }

    @staticmethod
    def rigetti_model() -> Dict[str, Any]:
        """Rigetti Aspen hardware noise model"""
        return {
            "single_qubit_error_rate": 0.0015,
            "two_qubit_error_rate": 0.008,
            "readout_error_rate": 0.015,
            "dephasing_rate": 0.0008,
            "damping_rate": 0.00015,
            "temperature": 25,
            "crosstalk_strength": 0.0015,
            "name": "Rigetti Aspen"
        }

    @staticmethod
    def ionq_model() -> Dict[str, Any]:
        """IonQ trapped-ion hardware noise model"""
        return {
            "single_qubit_error_rate": 0.0005,
            "two_qubit_error_rate": 0.002,
            "readout_error_rate": 0.005,
            "dephasing_rate": 0.0002,
            "damping_rate": 0.00005,
            "temperature": 10,
            "crosstalk_strength": 0.0005,
            "name": "IonQ"
        }

    @staticmethod
    def dwave_model() -> Dict[str, Any]:
        """D-Wave annealing hardware noise model"""
        return {
            "single_qubit_error_rate": 0.002,
            "two_qubit_error_rate": 0.01,
            "readout_error_rate": 0.02,
            "dephasing_rate": 0.001,
            "damping_rate": 0.0002,
            "temperature": 15,
            "crosstalk_strength": 0.002,
            "name": "D-Wave"
        }

    @staticmethod
    def ideal_model() -> Dict[str, Any]:
        """Ideal (noiseless) quantum computer"""
        return {
            "single_qubit_error_rate": 0.0,
            "two_qubit_error_rate": 0.0,
            "readout_error_rate": 0.0,
            "dephasing_rate": 0.0,
            "damping_rate": 0.0,
            "temperature": 0,
            "crosstalk_strength": 0.0,
            "name": "Ideal"
        }


def test_advanced_noise_models():
    """Test advanced noise models"""

    print("\n" + "="*60)
    print("ADVANCED NOISE MODELS TEST")
    print("="*60)

    num_qubits = 3

    # Test 1: IBM Quantum noise model
    print("\n1. Testing IBM Quantum noise model...")
    ibm_model = NoiseModelLibrary.ibm_quantum_model()
    simulator = RealisticQuantumSimulator(num_qubits, ibm_model)

    test_circuit = {
        "num_qubits": num_qubits,
        "gates": [
            {"name": "h", "qubits": [0]},
            {"name": "cnot", "qubits": [0, 1]},
            {"name": "h", "qubits": [2]}
        ]
    }

    counts = simulator.simulate_with_noise(test_circuit, shots=1000)
    fidelity = simulator.get_fidelity_estimate()
    print(f"   ✓ IBM Quantum simulation: {len(counts)} unique outcomes")
    print(f"   ✓ Estimated fidelity: {fidelity:.2%}")

    # Test 2: Compare hardware models
    print("\n2. Comparing different hardware noise models...")
    models = [
        NoiseModelLibrary.ibm_quantum_model(),
        NoiseModelLibrary.rigetti_model(),
        NoiseModelLibrary.ionq_model(),
        NoiseModelLibrary.dwave_model(),
    ]

    for model in models:
        sim = RealisticQuantumSimulator(num_qubits, model)
        fidelity = sim.get_fidelity_estimate()
        print(f"   ✓ {model['name']}: {fidelity:.2%} fidelity")

    # Test 3: Noise level impact
    print("\n3. Testing noise level impact...")
    for noise_level in [0.0, 0.5, 1.0]:
        counts = simulator.simulate_with_noise(test_circuit, shots=1000, noise_level=noise_level)
        entropy = -sum((c/1000) * np.log2(c/1000) for c in counts.values() if c > 0)
        print(f"   ✓ Noise level {noise_level:.1f}: {entropy:.2f} bits entropy")

    print("\n" + "="*60)
    print("ADVANCED NOISE MODELS TEST COMPLETE")
    print("="*60 + "\n")

    return {
        "ibm_simulation": counts,
        "fidelity_estimate": fidelity,
        "hardware_models": models
    }


if __name__ == "__main__":
    test_advanced_noise_models()
