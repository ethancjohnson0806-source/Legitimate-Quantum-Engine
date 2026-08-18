"""Matrix Product State (MPS) simulator.
Handles ~20-50 qubits for low-entanglement circuits.
"""
import numpy as np

class MPSState:
    def __init__(self, n_qubits, bond_dim=32):
        self.n = n_qubits
        self.chi = bond_dim
        self.tensors = []
        for i in range(n_qubits):
            left = 1 if i == 0 else bond_dim
            right = 1 if i == n_qubits - 1 else bond_dim
            t = np.zeros((left, 2, right), dtype=complex)
            t[0, 0, 0] = 1.0  # product state |0...0>
            self.tensors.append(t)

    def apply_1q(self, gate, site):
        t = np.tensordot(gate, self.tensors[site], axes=(1, 1))
        self.tensors[site] = np.moveaxis(t, 0, 1)

    def apply_2q_nn(self, gate, s1, s2):
        """Apply 2-qubit gate to nearest-neighbor sites s1 < s2."""
        if s2 != s1 + 1:
            raise ValueError("MPS apply_2q_nn requires adjacent qubits. Use SWAP or linear ansatz.")
        T1 = self.tensors[s1]
        T2 = self.tensors[s2]
        theta = np.tensordot(T1, T2, axes=(2, 0))
        theta = theta.reshape(T1.shape[0], 4, T2.shape[2])
        U = gate.reshape(4, 4)
        theta = np.tensordot(U, theta, axes=(1, 1))
        theta = np.moveaxis(theta, 0, 1)
        theta_mat = theta.reshape(T1.shape[0] * 2, 2 * T2.shape[2])
        A, S, B = np.linalg.svd(theta_mat, full_matrices=False)
        chi_new = min(len(S), self.chi)
        A = A[:, :chi_new]
        S = S[:chi_new]
        B = B[:chi_new, :]
        self.tensors[s1] = A.reshape(T1.shape[0], 2, chi_new)
        self.tensors[s2] = (np.diag(S) @ B).reshape(chi_new, 2, T2.shape[2])

    def canonicalize(self):
        # Left-to-right
        for i in range(self.n - 1):
            T = self.tensors[i]
            mat = T.reshape(T.shape[0] * 2, T.shape[2])
            U, S, Vh = np.linalg.svd(mat, full_matrices=False)
            chi_new = min(len(S), self.chi)
            U = U[:, :chi_new]
            S = S[:chi_new]
            Vh = Vh[:chi_new, :]
            self.tensors[i] = U.reshape(T.shape[0], 2, chi_new)
            self.tensors[i + 1] = np.tensordot(np.diag(S) @ Vh, self.tensors[i + 1], axes=(1, 0))
            self.tensors[i + 1] = np.moveaxis(self.tensors[i + 1], 0, 2)
        # Right-to-left
        for i in range(self.n - 1, 0, -1):
            T = self.tensors[i]
            mat = T.reshape(T.shape[0], 2 * T.shape[2])
            U, S, Vh = np.linalg.svd(mat, full_matrices=False)
            chi_new = min(len(S), self.chi)
            U = U[:, :chi_new]
            S = S[:chi_new]
            Vh = Vh[:chi_new, :]
            self.tensors[i] = Vh.reshape(chi_new, 2, T.shape[2])
            self.tensors[i - 1] = np.tensordot(self.tensors[i - 1], U @ np.diag(S), axes=(2, 0))

    def to_statevector(self):
        result = self.tensors[0]
        for i in range(1, self.n):
            result = np.tensordot(result, self.tensors[i], axes=(-1, 0))
        return result.reshape(-1)

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
            c, t = args[0], args[1]
            if abs(c - t) != 1:
                raise ValueError("MPS CNOT only supports nearest neighbors in this version.")
            if c > t:
                c, t = t, c
                g = np.transpose(g.reshape(2, 2, 2, 2), (1, 0, 3, 2)).reshape(2, 2, 2, 2)
            self.apply_2q_nn(g, c, t)
        elif name in ("RX", "RY", "RZ"):
            theta = args[0]
            q = args[1]
            c, s = np.cos(theta / 2), np.sin(theta / 2)
            if name == "RX":
                g = np.array([[c, -1j * s], [-1j * s, c]], dtype=complex)
            elif name == "RY":
                g = np.array([[c, -s], [s, c]], dtype=complex)
            else:
                g = np.array([[c - 1j * s, 0], [0, c + 1j * s]], dtype=complex)
            self.apply_1q(g, q)
        elif name == "SWAP":
            g = np.zeros((2, 2, 2, 2), dtype=complex)
            g[0, 0, 0, 0] = g[0, 1, 1, 0] = g[1, 0, 0, 1] = g[1, 1, 1, 1] = 1
            c, t = args[0], args[1]
            if abs(c - t) != 1:
                raise ValueError("MPS SWAP only supports nearest neighbors.")
            if c > t:
                c, t = t, c
            self.apply_2q_nn(g, c, t)
