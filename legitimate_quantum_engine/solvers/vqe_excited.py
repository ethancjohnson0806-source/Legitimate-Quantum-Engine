"""
ssvqe_solver.py  —  Subspace-search VQE for excited states

Pure NumPy.  Phone-runnable.  Test-first.  Honest limitations.

Limitations
-----------
- n <= 10 qubits (2**10 = 1024, phone boundary for repeated optimization)
- Fixed-depth hardware-efficient ansatz (RY + CNOT layers)
- Gradient-free Nelder-Mead (pure NumPy, no scipy)
- Overlap penalty for orthogonality (not rigorous subspace projection)
- No noise model (ideal simulation only)

Y-phase convention:  Y = [[0,-i],[i,0]]  so  Y|0> = +i|1>
"""

import numpy as np

# ---------------------------------------------------------------------------
# Pure NumPy Nelder-Mead (replaces scipy.optimize.minimize)
# ---------------------------------------------------------------------------

def _nelder_mead(func, x0, maxiter=500, xatol=1e-5, fatol=1e-5):
    """
    Nelder-Mead simplex optimizer.  Pure NumPy.
    Returns a dict-like object with .x, .fun, .success, .nfev, .nit
    """
    x0 = np.asarray(x0, dtype=float)
    n = len(x0)
    alpha = 1.0
    gamma = 2.0
    rho = 0.5
    sigma = 0.5

    simplex = [x0.copy()]
    for i in range(n):
        x = x0.copy()
        if x[i] != 0:
            x[i] *= 1.05
        else:
            x[i] = 0.00025
        simplex.append(x)
    simplex = np.array(simplex)

    fvals = np.array([func(x) for x in simplex])
    nfev = len(fvals)

    for iteration in range(maxiter):
        order = np.argsort(fvals)
        simplex = simplex[order]
        fvals = fvals[order]

        best_f = fvals[0]
        worst_f = fvals[-1]

        x_range = np.max(np.abs(simplex[1:] - simplex[0]), axis=0)
        if np.max(x_range) < xatol and (worst_f - best_f) < fatol:
            break

        centroid = np.mean(simplex[:-1], axis=0)
        xr = centroid + alpha * (centroid - simplex[-1])
        fr = func(xr)
        nfev += 1

        if best_f <= fr < fvals[-2]:
            simplex[-1] = xr
            fvals[-1] = fr
            continue

        if fr < best_f:
            xe = centroid + gamma * (xr - centroid)
            fe = func(xe)
            nfev += 1
            if fe < fr:
                simplex[-1] = xe
                fvals[-1] = fe
            else:
                simplex[-1] = xr
                fvals[-1] = fr
            continue

        if fr < worst_f:
            xc = centroid + rho * (xr - centroid)
        else:
            xc = centroid + rho * (simplex[-1] - centroid)
        fc = func(xc)
        nfev += 1

        if fc < min(fr, worst_f):
            simplex[-1] = xc
            fvals[-1] = fc
            continue

        for i in range(1, len(simplex)):
            simplex[i] = simplex[0] + sigma * (simplex[i] - simplex[0])
            fvals[i] = func(simplex[i])
            nfev += 1

    order = np.argsort(fvals)
    simplex = simplex[order]
    fvals = fvals[order]

    class Result:
        pass
    res = Result()
    res.x = simplex[0]
    res.fun = fvals[0]
    res.success = True
    res.nfev = nfev
    res.nit = iteration + 1
    return res


# ---------------------------------------------------------------------------
# Gate primitives
# ---------------------------------------------------------------------------

PAULI = {
    'I': np.array([[1, 0], [0, 1]], dtype=complex),
    'X': np.array([[0, 1], [1, 0]], dtype=complex),
    'Y': np.array([[0, -1j], [1j, 0]], dtype=complex),
    'Z': np.array([[1, 0], [0, -1]], dtype=complex),
}


def rx(theta):
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    return np.array([[c, -1j * s], [-1j * s, c]], dtype=complex)


def ry(theta):
    c, s = np.cos(theta / 2), np.sin(theta / 2)
    return np.array([[c, -s], [s, c]], dtype=complex)


def rz(theta):
    return np.array([[np.exp(-1j * theta / 2), 0],
                      [0, np.exp(1j * theta / 2)]], dtype=complex)


def cnot(n, control, target):
    dim = 2 ** n
    U = np.zeros((dim, dim), dtype=complex)
    for b in range(dim):
        cb = (b >> control) & 1
        if cb:
            U[b ^ (1 << target), b] = 1
        else:
            U[b, b] = 1
    return U


# ---------------------------------------------------------------------------
# Ansatz
# ---------------------------------------------------------------------------

def _apply_layer(state, params, n, layer_idx):
    for q in range(n):
        theta = params[layer_idx * n + q]
        state = state.reshape([2] * n)
        axes = list(range(n))
        axes[q] = -1
        state = np.tensordot(ry(theta), state, axes=([1], [q]))
        perm = list(range(n))
        perm.insert(q, n)
        state = np.moveaxis(state, -1, q)
    for q in range(n - 1):
        state = state.reshape(dim := 2 ** n)
        state = cnot(n, q, q + 1) @ state
    return state


def ansatz_state(params, n, n_layers):
    state = np.zeros(2 ** n, dtype=complex)
    state[0] = 1.0
    for l in range(n_layers):
        state = _apply_layer(state, params, n, l)
    return state


def ansatz_state_with_init(params, n, n_layers, init_state):
    state = init_state.copy()
    for l in range(n_layers):
        state = _apply_layer(state, params, n, l)
    return state


# ---------------------------------------------------------------------------
# SS-VQE core
# ---------------------------------------------------------------------------

def _expectation(state, H):
    return (state.conj() @ (H @ state)).real


def _overlap(state1, state2):
    return abs(state1.conj() @ state2) ** 2


def _single_state_cost(params, H, n, n_layers, init_state, ortho_states, lambda_penalty):
    state = ansatz_state_with_init(params, n, n_layers, init_state)
    state = state / np.linalg.norm(state)
    energy = _expectation(state, H)
    penalty = 0.0
    for os in ortho_states:
        penalty += lambda_penalty * _overlap(state, os)
    return energy + penalty


def _ssvqe_cost(params_flat, H, n, n_layers, n_states, lambda_penalty,
                init_states, prev_params_list):
    params_per_state = n_layers * n
    total_cost = 0.0
    for k in range(n_states):
        pk = params_flat[k * params_per_state:(k + 1) * params_per_state]
        state_k = ansatz_state_with_init(pk, n, n_layers, init_states[k])
        norm = np.linalg.norm(state_k)
        if norm > 1e-12:
            state_k = state_k / norm
        energy = _expectation(state_k, H)
        overlap_penalty = 0.0
        for prev_params in prev_params_list:
            prev_state = ansatz_state_with_init(prev_params, n, n_layers, init_states[0])
            prev_state = prev_state / np.linalg.norm(prev_state)
            overlap_penalty += lambda_penalty * _overlap(state_k, prev_state)
        for j in range(k):
            pj = params_flat[j * params_per_state:(j + 1) * params_per_state]
            state_j = ansatz_state_with_init(pj, n, n_layers, init_states[j])
            state_j = state_j / np.linalg.norm(state_j)
            overlap_penalty += lambda_penalty * _overlap(state_k, state_j)
        total_cost += energy + overlap_penalty
    return total_cost


class SSVQE:
    def __init__(self, H, n, n_layers=2, mode='sequential', lambda_penalty=10.0,
                 maxiter=500, tol=1e-5):
        self.H = np.asarray(H, dtype=complex)
        self.n = n
        self.n_layers = n_layers
        self.mode = mode
        self.lambda_penalty = lambda_penalty
        self.maxiter = maxiter
        self.tol = tol
        if self.H.shape != (2**n, 2**n):
            raise ValueError("H shape mismatch")
        if not np.allclose(self.H, self.H.T.conj()):
            raise ValueError("H not Hermitian")
        if n > 10:
            raise ValueError("n > 10 exceeds phone-runnable limit")

    def solve(self, n_states=None, verbose=False):
        if n_states is None:
            n_states = 2**self.n
        n_states = min(n_states, 2**self.n)
        init_states = [np.zeros(2**self.n, dtype=complex) for _ in range(n_states)]
        for k in range(n_states):
            init_states[k][k] = 1.0
        results = []

        if self.mode == 'sequential':
            ortho_states = []
            for k in range(n_states):
                if verbose:
                    print(f"  Optimizing state {k}...")
                np.random.seed(42 + k)
                x0 = np.random.randn(self.n_layers * self.n) * 0.1
                def cost_fn(x):
                    return _single_state_cost(x, self.H, self.n, self.n_layers,
                                             init_states[k], ortho_states,
                                             self.lambda_penalty)
                res = _nelder_mead(cost_fn, x0, maxiter=self.maxiter,
                                   xatol=self.tol, fatol=self.tol)
                state = ansatz_state_with_init(res.x, self.n, self.n_layers, init_states[k])
                state = state / np.linalg.norm(state)
                energy = _expectation(state, self.H)
                results.append((energy, state, res.x))
                ortho_states.append(state)

        elif self.mode == 'simultaneous':
            if verbose:
                print(f"  Simultaneous optimization of {n_states} states...")
            np.random.seed(42)
            x0 = np.random.randn(n_states * self.n_layers * self.n) * 0.1
            def cost_fn(x):
                return _ssvqe_cost(x, self.H, self.n, self.n_layers, n_states,
                                  self.lambda_penalty, init_states, [])
            res = _nelder_mead(cost_fn, x0, maxiter=self.maxiter * n_states,
                               xatol=self.tol, fatol=self.tol)
            params_per_state = self.n_layers * self.n
            for k in range(n_states):
                pk = res.x[k * params_per_state:(k + 1) * params_per_state]
                state = ansatz_state_with_init(pk, self.n, self.n_layers, init_states[k])
                state = state / np.linalg.norm(state)
                energy = _expectation(state, self.H)
                results.append((energy, state, pk))
        else:
            raise ValueError("mode must be 'sequential' or 'simultaneous'")

        results.sort(key=lambda x: x[0])
        return results


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _test_ground_state():
    print("\n=== Test: Ground State ===")
    n = 3
    dim = 2**n
    Z = PAULI['Z']
    X = PAULI['X']
    I = PAULI['I']
    H = np.zeros((dim, dim), dtype=complex)
    H -= np.kron(np.kron(Z, Z), I)
    H -= np.kron(np.kron(I, Z), Z)
    H -= np.kron(np.kron(X, I), I)
    H -= np.kron(np.kron(I, X), I)
    H -= np.kron(np.kron(I, I), X)
    exact = np.linalg.eigvalsh(H)[0]
    solver = SSVQE(H, n, n_layers=2, mode='sequential', maxiter=800)
    results = solver.solve(n_states=1, verbose=False)
    vqe_energy = results[0][0]
    assert abs(vqe_energy - exact) < 0.1
    print(f"  VQE={vqe_energy:.6f}, Exact={exact:.6f}, Error={abs(vqe_energy-exact):.6f}  PASS")


def _test_excited_states():
    print("\n=== Test: Excited States ===")
    n = 3
    dim = 2**n
    Z = PAULI['Z']
    X = PAULI['X']
    I = PAULI['I']
    H = np.zeros((dim, dim), dtype=complex)
    H -= np.kron(np.kron(Z, Z), I)
    H -= np.kron(np.kron(I, Z), Z)
    H -= 0.5 * np.kron(np.kron(X, I), I)
    H -= 0.5 * np.kron(np.kron(I, X), I)
    H -= 0.5 * np.kron(np.kron(I, I), X)
    exact_eigs = sorted(np.linalg.eigvalsh(H))
    solver = SSVQE(H, n, n_layers=3, mode='sequential', lambda_penalty=30.0, maxiter=800)
    results = solver.solve(n_states=2, verbose=False)
    vqe_eigs = [r[0] for r in results[:2]]
    for k, (v, e) in enumerate(zip(vqe_eigs, exact_eigs[:2])):
        assert abs(v - e) < 0.15
    print(f"  errors={[abs(v-e) for v,e in zip(vqe_eigs, exact_eigs[:2])]}  PASS")


def _test_orthogonality():
    print("\n=== Test: Orthogonality ===")
    n = 3
    dim = 2**n
    np.random.seed(7)
    A = np.random.randn(dim, dim) + 1j * np.random.randn(dim, dim)
    H = (A + A.T.conj()) / 2
    solver = SSVQE(H, n, n_layers=2, mode='sequential', lambda_penalty=50.0, maxiter=500)
    results = solver.solve(n_states=3, verbose=False)
    for i in range(3):
        for j in range(i + 1, 3):
            ov = abs(results[i][1].conj() @ results[j][1])
            assert ov < 0.3
    print(f"  max overlap < 0.3  PASS")


def _test_simultaneous_mode():
    print("\n=== Test: Simultaneous Mode ===")
    n = 2
    dim = 2**n
    H = np.diag([1.0, 2.0, 3.0, 4.0]).astype(complex)
    solver = SSVQE(H, n, n_layers=1, mode='simultaneous', lambda_penalty=30.0, maxiter=1000)
    results = solver.solve(n_states=2, verbose=False)
    vqe_eigs = [r[0] for r in results[:2]]
    assert abs(vqe_eigs[0] - 1.0) < 0.15
    assert abs(vqe_eigs[1] - 2.0) < 0.3
    print(f"  energies={vqe_eigs}  PASS")


def run_tests():
    print("=" * 60)
    print("SS-VQE SOLVER TEST SUITE")
    print("=" * 60)
    _test_ground_state()
    _test_excited_states()
    _test_orthogonality()
    _test_simultaneous_mode()
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == '__main__':
    run_tests()
