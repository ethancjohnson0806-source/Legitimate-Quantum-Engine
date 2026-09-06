"""
uccsd_ansatz.py -- Legitimate Quantum Engine v5.0, Phase 2

Unitary Coupled Cluster with Singles and Doubles (UCCSD).
Builds parameterized circuits from fermionic excitations mapped to
qubits via Jordan-Wigner or Bravyi-Kitaev.

Pure NumPy.  Phone-runnable.  Honest limitations.
"""

import numpy as np
from itertools import combinations


class UCCSDAnsatz:
    """
    UCCSD ansatz for molecular VQE.

    Parameters
    ----------
    n_orbitals : int
        Number of spin orbitals (= n_qubits).
    n_electrons : int
        Number of electrons (assumes closed-shell, even).
    mapping : str
        "jordan_wigner" or "bravyi_kitaev".
    """

    def __init__(self, n_orbitals, n_electrons, mapping="jordan_wigner"):
        self.n = n_orbitals
        self.n_elec = n_electrons
        self.mapping = mapping
        self.n_occ = n_electrons // 2   # closed-shell
        self.n_virt = n_orbitals - self.n_occ
        self._build_excitations()
        self._map_to_qubits()

    def _build_excitations(self):
        """Build lists of single and double excitations."""
        occ = list(range(self.n_occ))
        virt = list(range(self.n_occ, self.n))
        self.singles = [(p, q) for p in virt for q in occ]
        self.doubles = []
        for p, r in combinations(virt, 2):
            for q, s in combinations(occ, 2):
                self.doubles.append((p, q, r, s))
        self.n_params = len(self.singles) + len(self.doubles)

    def _map_to_qubits(self):
        """Map fermionic excitations to Pauli strings."""
        from ..quantum_chemistry.fermionic_encoding import (
            jordan_wigner_creators, jordan_wigner_annihilators,
            bravyi_kitaev_creators, bravyi_kitaev_annihilators,
            multiply_pauli_strings, simplify_pauli_sum
        )

        if self.mapping == "jordan_wigner":
            creators = jordan_wigner_creators(self.n)
            anns = jordan_wigner_annihilators(self.n)
        elif self.mapping == "bravyi_kitaev":
            creators = bravyi_kitaev_creators(self.n)
            anns = bravyi_kitaev_annihilators(self.n)
        else:
            raise ValueError(f"Unknown mapping: {self.mapping}")

        # Singles: a^\u2020_p a_q - h.c.
        self.pauli_singles = []
        for p, q in self.singles:
            terms = []
            for cp, cops in creators[p]:
                for aq, aops in anns[q]:
                    terms.append(multiply_pauli_strings((cp, cops), (aq, aops)))
            for cq, cops in creators[q]:
                for ap, aops in anns[p]:
                    t = multiply_pauli_strings((cq, cops), (ap, aops))
                    terms.append((-t[0], t[1]))
            self.pauli_singles.append(simplify_pauli_sum(terms))

        # Doubles: a^\u2020_p a^\u2020_q a_r a_s - h.c.
        self.pauli_doubles = []
        for p, q, r, s in self.doubles:
            terms = []
            for cp, cops_p in creators[p]:
                for cq, cops_q in creators[q]:
                    t1 = multiply_pauli_strings((cp, cops_p), (cq, cops_q))
                    for ar, aops_r in anns[r]:
                        t2 = multiply_pauli_strings(t1, (ar, aops_r))
                        for ass, aops_s in anns[s]:
                            t3 = multiply_pauli_strings(t2, (ass, aops_s))
                            terms.append(t3)
            for cs, cops_s in creators[s]:
                for cr, cops_r in creators[r]:
                    t1 = multiply_pauli_strings((cs, cops_s), (cr, cops_r))
                    for aq, aops_q in anns[q]:
                        t2 = multiply_pauli_strings(t1, (aq, aops_q))
                        for ap, aops_p in anns[p]:
                            t3 = multiply_pauli_strings(t2, (ap, aops_p))
                            terms.append((-t3[0], t3[1]))
            self.pauli_doubles.append(simplify_pauli_sum(terms))

    def build_circuit(self, params=None):
        if params is None:
            params = np.zeros(self.n_params)
        if len(params) != self.n_params:
            raise ValueError(f"Expected {self.n_params} params, got {len(params)}")
        circuit = []
        idx = 0
        for i, _ in enumerate(self.singles):
            circuit.append(("excitation_single", i, params[idx])); idx += 1
        for i, _ in enumerate(self.doubles):
            circuit.append(("excitation_double", i, params[idx])); idx += 1
        return circuit

    def initial_parameters(self):
        return np.random.normal(0, 0.01, size=self.n_params)

    def apply_to_sim(self, sim, params):
        idx = 0
        for i, _ in enumerate(self.singles):
            self._apply_single_excitation(sim, i, params[idx]); idx += 1
        for i, _ in enumerate(self.doubles):
            self._apply_double_excitation(sim, i, params[idx]); idx += 1

    def _apply_single_excitation(self, sim, idx, theta):
        terms = self.pauli_singles[idx]
        for coeff, ops in terms:
            alpha = theta * coeff.real
            if abs(alpha) > 1e-15:
                self._apply_pauli_rotation(sim, ops, alpha)

    def _apply_double_excitation(self, sim, idx, theta):
        terms = self.pauli_doubles[idx]
        for coeff, ops in terms:
            alpha = theta * coeff.real
            if abs(alpha) > 1e-15:
                self._apply_pauli_rotation(sim, ops, alpha)

    def _apply_pauli_rotation(self, sim, ops, alpha):
        non_id = [(idx, p) for idx, p in ops if p != 'I']
        if not non_id:
            return
        if len(non_id) == 1:
            q, p = non_id[0]
            if p == 'X': sim.apply("RX", 2 * alpha, q)
            elif p == 'Y': sim.apply("RY", 2 * alpha, q)
            elif p == 'Z': sim.apply("RZ", 2 * alpha, q)
        else:
            qubits = [q for q, _ in non_id]
            for q, p in non_id:
                if p == 'X': sim.apply("H", q)
                elif p == 'Y': sim.apply("RX", np.pi / 2, q)
            for i in range(len(qubits) - 1):
                sim.apply("CNOT", qubits[i], qubits[i + 1])
            sim.apply("RZ", 2 * alpha, qubits[-1])
            for i in range(len(qubits) - 2, -1, -1):
                sim.apply("CNOT", qubits[i], qubits[i + 1])
            for q, p in non_id:
                if p == 'X': sim.apply("H", q)
                elif p == 'Y': sim.apply("RX", -np.pi / 2, q)

    @property
    def num_parameters(self):
        return self.n_params

    def __repr__(self):
        return (f"UCCSDAnsatz(n_orbitals={self.n}, n_electrons={self.n_elec}, "
                f"mapping={self.mapping!r}, n_params={self.n_params})")


def test_uccsd_h2():
    print("\n=== Test: UCCSD H2 ===")
    ansatz = UCCSDAnsatz(n_orbitals=4, n_electrons=2, mapping="jordan_wigner")
    assert ansatz.num_parameters > 0
    params = ansatz.initial_parameters()
    circuit = ansatz.build_circuit(params)
    assert len(circuit) == ansatz.num_parameters
    print(f"  PASS  (n_params={ansatz.num_parameters})")


def test_uccsd_lih():
    print("\n=== Test: UCCSD LiH ===")
    ansatz = UCCSDAnsatz(n_orbitals=12, n_electrons=4, mapping="bravyi_kitaev")
    assert ansatz.num_parameters > 0
    print(f"  PASS  (n_params={ansatz.num_parameters})")


def test_jw_vs_bk():
    print("\n=== Test: JW vs BK ===")
    jw = UCCSDAnsatz(n_orbitals=6, n_electrons=2, mapping="jordan_wigner")
    bk = UCCSDAnsatz(n_orbitals=6, n_electrons=2, mapping="bravyi_kitaev")
    assert jw.num_parameters == bk.num_parameters
    print(f"  PASS  (JW={jw.num_parameters}, BK={bk.num_parameters})")


def test_apply_to_sim():
    print("\n=== Test: Apply to StatevectorSim ===")
    from ..core.statevector import StatevectorSim
    ansatz = UCCSDAnsatz(n_orbitals=4, n_electrons=2, mapping="jordan_wigner")
    sim = StatevectorSim(4)
    params = ansatz.initial_parameters()
    ansatz.apply_to_sim(sim, params)
    nrm = np.linalg.norm(sim.state)
    assert abs(nrm - 1.0) < 1e-10
    print(f"  PASS  (norm={nrm:.6f})")


def run_all_tests():
    print("=" * 60)
    print("UCCSD ANSATZ TEST SUITE")
    print("=" * 60)
    test_uccsd_h2()
    test_uccsd_lih()
    test_jw_vs_bk()
    test_apply_to_sim()
    print("\n" + "=" * 60)
    print("ALL UCCSD TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
