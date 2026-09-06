"""Quantum Natural Gradient optimizer.
Uses the Quantum Fisher Information matrix to precondition gradients.
"""
import numpy as np

class QNGOptimizer:
    def __init__(self, ansatz_func, n_qubits, hamiltonian):
        self.ansatz = ansatz_func
        self.n = n_qubits
        self.H = hamiltonian

    def energy_and_state(self, params):
        sim = self.ansatz(params, self.n)
        e = float(np.real(np.vdot(sim.state, self.H @ sim.state)))
        return e, sim.state

    def qfi_matrix(self, params, epsilon=1e-4):
        d = len(params)
        _, psi0 = self.energy_and_state(params)
        d_psi = []
        eye = np.eye(d)
        for i in range(d):
            _, psi_plus = self.energy_and_state(params + epsilon * eye[i])
            dpsi = (psi_plus - psi0) / epsilon
            d_psi.append(dpsi)
        G = np.zeros((d, d))
        for i in range(d):
            for j in range(i, d):
                g = np.real(
                    np.vdot(d_psi[i], d_psi[j])
                    - np.vdot(d_psi[i], psi0) * np.vdot(psi0, d_psi[j])
                )
                G[i, j] = g
                G[j, i] = g
        return G

    def optimize(self, params_init, max_iter=100, verbose=False):
        params = np.array(params_init, dtype=float)
        for k in range(max_iter):
            e, _ = self.energy_and_state(params)
            grad = np.zeros(len(params))
            eye = np.eye(len(params))
            for i in range(len(params)):
                e_plus, _ = self.energy_and_state(params + 1e-4 * eye[i])
                e_minus, _ = self.energy_and_state(params - 1e-4 * eye[i])
                grad[i] = (e_plus - e_minus) / 2e-4
            G = self.qfi_matrix(params) + 1e-3 * np.eye(len(params))
            nat_grad = np.linalg.solve(G, grad)
            best_e = e
            best_alpha = 0
            for alpha in [0.01, 0.05, 0.1, 0.2, 0.5]:
                e_new, _ = self.energy_and_state(params - alpha * nat_grad)
                if e_new < best_e:
                    best_e = e_new
                    best_alpha = alpha
            if best_alpha > 0:
                params = params - best_alpha * nat_grad
            else:
                break
            if verbose and k % 10 == 0:
                print(f"QNG iter {k}: energy={best_e:.6f}")
        e_final, _ = self.energy_and_state(params)
        return e_final, params
