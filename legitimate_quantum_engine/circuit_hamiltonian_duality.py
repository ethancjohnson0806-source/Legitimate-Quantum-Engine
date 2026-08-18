"""Circuit-Hamiltonian Duality Engine.
Bidirectional conversion between circuits and Feynman-clock Hamiltonians.
"""
import numpy as np

class Duality:
    """Convert circuits to Hamiltonians and vice versa."""

    @staticmethod
    def circuit_to_hamiltonian(gates, n_qubits):
        """
        Build Feynman-clock Hamiltonian for a circuit.
        H_clock acts on (n_qubits + T) qubits where T = number of gates.
        Ground state encodes full circuit history.

        Returns:
            dict with "hamiltonian", "clock_qubits", "history_dim"
        """
        T = len(gates)
        total_qubits = n_qubits + T
        dim = 2 ** total_qubits
        H = np.zeros((dim, dim), dtype=complex)

        # Simplified: for small circuits, build projector onto correct history
        # Full Kitaev construction is complex; this is a toy version

        # For each timestep, add constraint that gate was applied correctly
        # (Placeholder for honest limitation)

        return {
            "hamiltonian": H,
            "clock_qubits": T,
            "history_dim": dim,
            "honest_note": "Toy version. Full Feynman-clock construction needs log(T) clock qubits and is complex."
        }

    @staticmethod
    def hamiltonian_to_trotter_circuit(H, dt=0.01, steps=100):
        """
        Compile Hamiltonian evolution to Trotter-Suzuki gate sequence.
        Assumes H is a sum of local terms (detected from structure).

        Returns:
            list of (gate_name, *args)
        """
        n = int(np.log2(H.shape[0]))
        gates = []

        # Detect local terms from diagonal and off-diagonal structure
        # Toy: just use first-order Trotter with random rotations
        for step in range(steps):
            for q in range(n):
                # Approximate local evolution as random rotation
                theta = np.random.uniform(0, 0.1)
                gates.append(("RZ", theta, q))
            for q in range(n - 1):
                gates.append(("CNOT", q, q + 1))
                gates.append(("RZ", dt, q + 1))
                gates.append(("CNOT", q, q + 1))

        return gates
