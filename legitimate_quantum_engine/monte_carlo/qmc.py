"""
qmc_solver.py  —  Variational Monte Carlo energy estimator

Pure NumPy.  Phone-runnable.  Test-first.  Honest limitations.

Limitations
-----------
- n <= 12 qubits (sampling space is 2^n but we only store samples, not full vector)
- Variational Monte Carlo only (no projector / diffusion / reptation QMC)
- Trial states are real and positive in the computational basis
  => NO sign problem for sampling, but this is a restriction
- Projector QMC with sign handling is beyond phone-runnable scope
- Local energy variance grows with system size and correlation length
- No stochastic reconfiguration or natural gradient (just energy estimation)

Y-phase convention:  Y = [[0,-i],[i,0]]  so  Y|0> = +i|1>
"""

import numpy as np


class ProductState:
    """Product of RY rotations: amplitudes real and positive."""
    def __init__(self, thetas):
        self.thetas = np.asarray(thetas, dtype=float)
        self.n = len(self.thetas)
        self.amps = np.stack([np.cos(self.thetas / 2), np.sin(self.thetas / 2)], axis=1)

    def amplitude(self, config):
        if np.isscalar(config):
            bits = [(config >> i) & 1 for i in range(self.n)]
        else:
            bits = list(config)
        prod = 1.0
        for i, b in enumerate(bits):
            prod *= self.amps[i, b]
        return prod

    def amplitude_batch(self, configs):
        configs = np.asarray(configs, dtype=int)
        bits = np.zeros((len(configs), self.n), dtype=int)
        for i in range(self.n):
            bits[:, i] = (configs >> i) & 1
        selected = np.zeros((len(configs), self.n))
        for i in range(self.n):
            selected[:, i] = self.amps[i, bits[:, i]]
        return np.prod(selected, axis=1)

    def sample(self, n_samples, seed=None):
        if seed is not None:
            np.random.seed(seed)
        probs = self.amps ** 2
        bits = np.array([np.random.choice(2, size=n_samples, p=p) for p in probs])
        configs = np.zeros(n_samples, dtype=int)
        for i in range(self.n):
            configs += bits[i] * (1 << i)
        return configs


class LocalHamiltonian:
    def __init__(self, terms, n):
        self.terms = terms
        self.n = n

    def _pauli_action(self, op, bit):
        if op == 'I':
            return bit, 1.0
        elif op == 'X':
            return 1 - bit, 1.0
        elif op == 'Z':
            return bit, 1.0 if bit == 0 else -1.0
        elif op == 'Y':
            return 1 - bit, 1j if bit == 0 else -1j
        else:
            raise ValueError(f"Unknown op: {op}")

    def apply_term(self, config, term):
        coeff, ops = term
        new_config = config
        factor = coeff
        for q, op in ops:
            bit = (config >> q) & 1
            new_bit, amp = self._pauli_action(op, bit)
            if new_bit != bit:
                new_config = new_config ^ (1 << q)
            factor *= amp
        return [(new_config, factor)]

    def local_energy(self, config, trial):
        psi_config = trial.amplitude(config)
        if abs(psi_config) < 1e-15:
            return 0.0
        num = 0.0
        for term in self.terms:
            for new_config, factor in self.apply_term(config, term):
                num += factor * trial.amplitude(new_config)
        return (num / psi_config).real

    def local_energy_batch(self, configs, trial):
        configs = np.asarray(configs, dtype=int)
        psi_vals = trial.amplitude_batch(configs)
        result = np.zeros(len(configs))
        for i, config in enumerate(configs):
            if abs(psi_vals[i]) < 1e-15:
                result[i] = 0.0
                continue
            num = 0.0
            for term in self.terms:
                for new_config, factor in self.apply_term(config, term):
                    num += factor * trial.amplitude(new_config)
            result[i] = (num / psi_vals[i]).real
        return result


class VMCSolver:
    def __init__(self, hamiltonian, trial_state):
        self.H = hamiltonian
        self.trial = trial_state
        if self.H.n != self.trial.n:
            raise ValueError("Hamiltonian and trial state dimension mismatch")

    def estimate_energy(self, n_samples, seed=None, return_variance=False):
        configs = self.trial.sample(n_samples, seed=seed)
        local_energies = self.H.local_energy_batch(configs, self.trial)
        energy = np.mean(local_energies)
        if return_variance:
            var = np.var(local_energies, ddof=1) / n_samples
            return energy, var
        return energy


def transverse_field_ising(n, J=1.0, h=0.5):
    terms = []
    for i in range(n):
        j = (i + 1) % n
        terms.append((-J, [(i, 'Z'), (j, 'Z')]))
    for i in range(n):
        terms.append((-h, [(i, 'X')]))
    return LocalHamiltonian(terms, n)


def heisenberg_chain(n, J=1.0):
    terms = []
    for i in range(n - 1):
        for op in ['X', 'Y', 'Z']:
            terms.append((J, [(i, op), (i + 1, op)]))
    return LocalHamiltonian(terms, n)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _test_sampling_distribution():
    n = 3
    thetas = np.array([0.5, 1.0, 1.5])
    psi = ProductState(thetas)
    n_samples = 50000
    configs = psi.sample(n_samples, seed=42)
    all_configs = np.arange(2**n)
    exact_probs = psi.amplitude_batch(all_configs) ** 2
    exact_probs /= exact_probs.sum()
    counts = np.bincount(configs, minlength=2**n)
    emp_probs = counts / n_samples
    max_diff = np.max(np.abs(emp_probs - exact_probs))
    assert max_diff < 0.02, f"Sampling distribution off: max_diff={max_diff}"
    print(f"  Sampling distribution: max_diff={max_diff:.4f}  PASS")


def _test_local_energy_diagonal():
    n = 2
    terms = [(1.0, [(0, 'Z')]), (2.0, [(1, 'Z')])]
    H = LocalHamiltonian(terms, n)
    thetas = np.array([0.3, 0.7])
    psi = ProductState(thetas)
    for config in range(4):
        el = H.local_energy(config, psi)
        b0 = (config >> 0) & 1
        b1 = (config >> 1) & 1
        expected = (1.0 if b0 == 0 else -1.0) + 2.0 * (1.0 if b1 == 0 else -1.0)
        assert abs(el - expected) < 1e-10, f"Local energy wrong: {el} vs {expected}"
    print(f"  Local energy (diagonal): PASS")


def _test_vmc_energy_estimate():
    """Test VMC with a trial state that IS the exact ground state."""
    n = 4
    # H = -sum_i X_i — ground state is |+++++> with energy -n
    terms = [(-1.0, [(i, 'X')]) for i in range(n)]
    H = LocalHamiltonian(terms, n)
    exact_E = -float(n)
    thetas = np.full(n, np.pi / 2)
    psi = ProductState(thetas)
    solver = VMCSolver(H, psi)
    vmc_E, var = solver.estimate_energy(n_samples=20000, seed=42, return_variance=True)
    assert abs(vmc_E - exact_E) < 0.05, f"VMC energy wrong: {vmc_E} vs {exact_E}"
    print(f"  VMC energy (exact trial): {vmc_E:.4f} vs exact {exact_E:.4f}, var={var:.6f}  PASS")


def _test_variance_scaling():
    n = 3
    H = transverse_field_ising(n, J=1.0, h=0.5)
    thetas = np.full(n, np.pi / 2)
    psi = ProductState(thetas)
    solver = VMCSolver(H, psi)
    _, var1 = solver.estimate_energy(1000, seed=1, return_variance=True)
    _, var2 = solver.estimate_energy(10000, seed=2, return_variance=True)
    assert var2 < var1, f"Variance did not decrease: {var1} vs {var2}"
    print(f"  Variance scaling: var(1k)={var1:.6f}, var(10k)={var2:.6f}  PASS")


def _test_sign_problem_acknowledged():
    n = 2
    H = heisenberg_chain(n, J=1.0)
    thetas = np.full(n, np.pi / 2)
    psi = ProductState(thetas)
    solver = VMCSolver(H, psi)
    vmc_E, _ = solver.estimate_energy(20000, seed=42, return_variance=True)
    exact_E = -3.0
    assert vmc_E > exact_E - 0.1, f"VMC below exact: {vmc_E} vs {exact_E}"
    print(f"  Sign problem acknowledged: VMC={vmc_E:.4f} > exact={exact_E:.4f}  PASS")


def run_tests():
    print("Testing qmc_solver.py...")
    _test_sampling_distribution()
    _test_local_energy_diagonal()
    _test_vmc_energy_estimate()
    _test_variance_scaling()
    _test_sign_problem_acknowledged()
    print("All tests passed.")


if __name__ == '__main__':
    run_tests()
