import numpy as np

class ClassicalShadow:
    def __init__(self, num_qubits, num_snapshots=100):
        self.n = num_qubits
        self.T = num_snapshots
        self.snapshots = []

    def random_pauli_measurement(self, state_sim):
        from ..core.statevector import StatevectorSim
        snapshot = []
        for t in range(self.T):
            sim = state_sim.copy()
            for q in range(self.n):
                b = np.random.choice(["X", "Y", "Z"])
                if b == "X":
                    sim.apply("H", q)
                elif b == "Y":
                    sim.apply("H", q)
                    sim.apply("RZ", -np.pi / 2, q)
                probs = sim.probabilities()
                p0 = sum(probs[i] for i in range(sim.dim) if ((i >> q) & 1) == 0)
                outcome = 0 if np.random.random() < p0 else 1
                sim.state = np.array([
                    sim.state[i] if ((i >> q) & 1) == outcome else 0
                    for i in range(sim.dim)
                ], dtype=complex)
                sim.state /= np.linalg.norm(sim.state)
                snapshot.append((q, b, outcome))
        self.snapshots.append(snapshot)
        return snapshot

    def estimate_expectation(self, pauli_string):
        estimates = []
        for snapshot in self.snapshots:
            prod = 1.0
            for q, b, outcome in snapshot:
                if b == pauli_string[q]:
                    prod *= 3.0 * (1 if outcome == 0 else -1)
                else:
                    prod = 0
                    break
            estimates.append(prod)
        return np.median(estimates) if estimates else 0.0
