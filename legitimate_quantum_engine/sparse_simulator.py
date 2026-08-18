"""Sparse State Simulator — stores only non-zero amplitudes."""
import numpy as np

class SparseStateSimulator:
    def __init__(self, num_qubits):
        self.n = num_qubits
        self.state = {0: 1.0 + 0j}

    def apply_1q(self, gate, target):
        new_state = {}
        for idx, amp in self.state.items():
            bit = (idx >> target) & 1
            other = idx & ~(1 << target)
            for b in (0, 1):
                new_idx = other | (b << target)
                new_amp = amp * gate[b, bit]
                if abs(new_amp) > 1e-15:
                    new_state[new_idx] = new_state.get(new_idx, 0) + new_amp
        self.state = new_state

    def apply_2q(self, gate, control, target):
        new_state = {}
        for idx, amp in self.state.items():
            c_bit = (idx >> control) & 1
            t_bit = (idx >> target) & 1
            other = idx & ~((1 << control) | (1 << target))
            for cb in (0, 1):
                for tb in (0, 1):
                    new_idx = other | (cb << control) | (tb << target)
                    new_amp = amp * gate[cb, tb, c_bit, t_bit]
                    if abs(new_amp) > 1e-15:
                        new_state[new_idx] = new_state.get(new_idx, 0) + new_amp
        self.state = new_state

    def apply(self, name, *args):
        if name == "H":
            g = np.array([[1, 1], [1, -1]], dtype=complex) / np.sqrt(2)
            self.apply_1q(g, args[0])
        elif name == "X":
            g = np.array([[0, 1], [1, 0]], dtype=complex)
            self.apply_1q(g, args[0])
        elif name == "CNOT":
            g = np.zeros((2, 2, 2, 2), dtype=complex)
            g[0, 0, 0, 0] = g[0, 1, 0, 1] = g[1, 0, 1, 1] = g[1, 1, 1, 0] = 1
            self.apply_2q(g, args[0], args[1])
        elif name in ("RX", "RY", "RZ"):
            theta = args[0]
            if name == "RX":
                c, s = np.cos(theta / 2), np.sin(theta / 2)
                g = np.array([[c, -1j * s], [-1j * s, c]], dtype=complex)
            elif name == "RY":
                c, s = np.cos(theta / 2), np.sin(theta / 2)
                g = np.array([[c, -s], [s, c]], dtype=complex)
            else:
                c, s = np.cos(theta / 2), np.sin(theta / 2)
                g = np.array([[c - 1j * s, 0], [0, c + 1j * s]], dtype=complex)
            self.apply_1q(g, args[1])

    def probabilities(self):
        return {k: abs(v) ** 2 for k, v in self.state.items()}

    def sample(self, n_shots=1024):
        indices = list(self.state.keys())
        probs = np.array([abs(self.state[i]) ** 2 for i in indices])
        probs /= probs.sum()
        return np.random.choice(indices, size=n_shots, p=probs)

    def expectation(self, operator_dict):
        total = 0
        for (i, j), val in operator_dict.items():
            if i in self.state and j in self.state:
                total += np.conj(self.state[i]) * val * self.state[j]
        return float(np.real(total))

    def measure(self, qubit):
        p0 = sum(abs(v) ** 2 for k, v in self.state.items() if ((k >> qubit) & 1) == 0)
        outcome = 0 if np.random.random() < p0 else 1
        self.state = {
            k: v for k, v in self.state.items()
            if ((k >> qubit) & 1) == outcome
        }
        norm = np.sqrt(sum(abs(v) ** 2 for v in self.state.values()))
        self.state = {k: v / norm for k, v in self.state.items()}
        return outcome
