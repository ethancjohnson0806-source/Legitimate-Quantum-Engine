"""ADAPT-VQE: operator-pool ansatz builder.
Builds the circuit one operator at a time based on gradients.
"""
import numpy as np
from .core_simulator import StatevectorSim

def apply_pauli_string(state, n, pauli_list):
    """Apply a Pauli string [(qubit, 'X'/'Y'/'Z'), ...] to a statevector."""
    new_state = state.copy()
    for q, p in pauli_list:
        shape = [2] * n
        psi = new_state.reshape(shape)
        psi = np.moveaxis(psi, q, 0)
        if p == "X":
            P = np.array([[0, 1], [1, 0]], dtype=complex)
        elif p == "Y":
            P = np.array([[0, -1j], [1j, 0]], dtype=complex)
        else:
            P = np.array([[1, 0], [0, -1]], dtype=complex)
        psi = np.tensordot(P, psi, axes=(1, 0))
        psi = np.moveaxis(psi, 0, q)
        new_state = psi.reshape(2 ** n)
    return new_state

def build_operator_pool(n_qubits):
    """Build a qubit-ADAPT pool: singles + doubles Pauli strings."""
    pool = []
    # Single-qubit X, Y
    for q in range(n_qubits):
        for p in ["X", "Y"]:
            pool.append([(q, p)])
    # Two-qubit strings on all pairs
    for i in range(n_qubits):
        for j in range(i + 1, n_qubits):
            for p1 in ["X", "Y", "Z"]:
                for p2 in ["X", "Y", "Z"]:
                    pool.append([(i, p1), (j, p2)])
    return pool

class ADAPTVQE:
    def __init__(self, n_qubits, hamiltonian, operator_pool=None,
                 gradient_thresh=1e-3, max_operators=20, max_iterations_per_opt=300):
        self.n = n_qubits
        self.H = hamiltonian
        self.pool = operator_pool or build_operator_pool(n_qubits)
        self.thresh = gradient_thresh
        self.max_ops = max_operators
        self.max_iter = max_iterations_per_opt
        self.ansatz_ops = []
        self.params = []
        self.exact = np.min(np.linalg.eigvalsh(self.H))

    def get_statevector(self, params=None):
        if params is None:
            params = self.params
        sim = StatevectorSim(self.n)
        for op, theta in zip(self.ansatz_ops, params):
            p_state = apply_pauli_string(sim.state, self.n, op)
            # e^{-i theta P / 2} = cos(theta/2) I - i sin(theta/2) P
            sim.state = np.cos(theta / 2) * sim.state - 1j * np.sin(theta / 2) * p_state
            nrm = np.linalg.norm(sim.state)
            if nrm > 0:
                sim.state /= nrm
        return sim

    def energy(self, params=None):
        sim = self.get_statevector(params)
        return float(np.real(np.vdot(sim.state, self.H @ sim.state)))

    def gradient(self, op):
        sim = self.get_statevector()
        psi = sim.state
        Hpsi = self.H @ psi
        Ppsi = apply_pauli_string(psi, self.n, op)
        # For U = e^{-i theta P/2}, dE/dtheta = Im(<Hpsi|Ppsi>)
        return np.imag(np.vdot(Hpsi, Ppsi))

    def _optimize_params(self, verbose):
        try:
            from scipy.optimize import minimize
            result = minimize(self.energy, self.params, method="BFGS",
                              options={"maxiter": self.max_iter, "disp": verbose})
            self.params = list(result.x)
            return result.fun
        except ImportError:
            return self._coordinate_descent(verbose)

    def _coordinate_descent(self, verbose):
        for it in range(self.max_iter):
            improved = False
            for i in range(len(self.params)):
                best_e = self.energy()
                best_t = self.params[i]
                for delta in np.linspace(-0.3, 0.3, 7):
                    old = self.params[i]
                    self.params[i] += delta
                    e = self.energy()
                    if e < best_e:
                        best_e = e
                        best_t = self.params[i]
                    else:
                        self.params[i] = old
                if best_t != self.params[i]:
                    self.params[i] = best_t
                    improved = True
            if not improved:
                break
        return self.energy()

    def solve(self, verbose=False):
        for iteration in range(self.max_ops):
            best_grad = 0.0
            best_op = None
            for op in self.pool:
                g = abs(self.gradient(op))
                if g > best_grad:
                    best_grad = g
                    best_op = op
            if verbose:
                print(f"ADAPT iter {iteration}: best |grad| = {best_grad:.6f}")
            if best_grad < self.thresh:
                if verbose:
                    print("Converged: gradient below threshold")
                break
            self.ansatz_ops.append(best_op)
            self.params.append(0.0)
            e = self._optimize_params(verbose)
            err = abs(e - self.exact) / abs(self.exact) if self.exact != 0 else abs(e)
            if verbose:
                print(f"  Energy: {e:.6f}, exact: {self.exact:.6f}, error: {err:.4f}")
        e = self.energy()
        err = abs(e - self.exact) / abs(self.exact) if self.exact != 0 else abs(e)
        return {
            "energy": e,
            "exact": self.exact,
            "error": abs(e - self.exact),
            "relative_error": err,
            "parameters": self.params,
            "operators": [str(op) for op in self.ansatz_ops],
            "converged": err < 0.15,
            "status": "PASS" if err < 0.15 else "NEEDS_MORE_ITERATIONS"
        }
