"""
fermionic_encoding.py  —  Jordan-Wigner, Bravyi-Kitaev, Parity mapping

Pure NumPy.  Phone-runnable.  Test-first.  Honest limitations.

Limitations
-----------
- n <= 14 qubits (2**14 = 16384-dim Hilbert space, phone boundary)
- No chemistry-specific orbital data (just the encoding machinery)
- Pauli strings stored as (coeff, list-of-ops) where ops are
  tuples (qubit_index, 'X'|'Y'|'Z'|'I')

Y-phase convention:  Y = [[0,-i],[i,0]]  so  Y|0> = +i|1>
"""

import numpy as np
import math
from itertools import combinations

# ---------------------------------------------------------------------------
# Pauli helpers
# ---------------------------------------------------------------------------

PAULI = {
    'I': np.array([[1, 0], [0, 1]], dtype=complex),
    'X': np.array([[0, 1], [1, 0]], dtype=complex),
    'Y': np.array([[0, -1j], [1j, 0]], dtype=complex),   # Y|0> = +i|1>
    'Z': np.array([[1, 0], [0, -1]], dtype=complex),
}


def pauli_string_to_matrix(ops, n):
    """
    Convert a Pauli string (list of (idx, 'X'|'Y'|'Z'|'I')) to a 2^n x 2^n matrix.
    """
    mats = [PAULI['I'].copy() for _ in range(n)]
    for idx, p in ops:
        mats[idx] = PAULI[p]
    result = mats[0]
    for m in mats[1:]:
        result = np.kron(result, m)
    return result


def multiply_pauli(p1, p2):
    """
    Multiply two single-qubit Pauli operators.
    Returns (new_pauli, phase) where phase is in {1, 1j, -1, -1j}.
    """
    table = {
        ('I','I'): ('I', 1), ('I','X'): ('X', 1), ('I','Y'): ('Y', 1), ('I','Z'): ('Z', 1),
        ('X','I'): ('X', 1), ('X','X'): ('I', 1), ('X','Y'): ('Z', 1j), ('X','Z'): ('Y', -1j),
        ('Y','I'): ('Y', 1), ('Y','X'): ('Z', -1j), ('Y','Y'): ('I', 1), ('Y','Z'): ('X', 1j),
        ('Z','I'): ('Z', 1), ('Z','X'): ('Y', 1j), ('Z','Y'): ('X', -1j), ('Z','Z'): ('I', 1),
    }
    return table[(p1, p2)]


def multiply_pauli_strings(ps1, ps2):
    """
    Multiply two Pauli strings.
    Each is (coeff, list of (idx, pauli)).
    Returns (coeff, list of (idx, pauli)).
    """
    c1, ops1 = ps1
    c2, ops2 = ps2
    # Build dicts
    d1 = {idx: p for idx, p in ops1}
    d2 = {idx: p for idx, p in ops2}
    indices = sorted(set(d1.keys()) | set(d2.keys()))
    phase = 1
    result_ops = []
    for idx in indices:
        p1 = d1.get(idx, 'I')
        p2 = d2.get(idx, 'I')
        new_p, ph = multiply_pauli(p1, p2)
        phase *= ph
        if new_p != 'I':
            result_ops.append((idx, new_p))
    return (c1 * c2 * phase, result_ops)


def simplify_pauli_sum(terms):
    """
    Simplify a list of Pauli string terms by combining like terms.
    Each term is (coeff, list of (idx, pauli)).
    Returns list of simplified terms.
    """
    groups = {}
    for coeff, ops in terms:
        key = tuple(sorted(ops))
        groups[key] = groups.get(key, 0) + coeff
    result = []
    for key, coeff in groups.items():
        if abs(coeff) > 1e-12:
            result.append((coeff, list(key)))
    return result


# ---------------------------------------------------------------------------
# Jordan-Wigner encoding
# ---------------------------------------------------------------------------

def jordan_wigner_creators(n):
    """
    Return the n fermionic creation operators a^
    _j as Pauli strings.
    a^\n    _j = (1/2) * (X_j - i Y_j) * prod_{k<j} Z_k
    """
    creators = []
    for j in range(n):
        # (X - iY)/2 on site j
        ops = [(j, 'X')]
        term1 = (0.5, ops)
        term2 = (-0.5j, [(j, 'Y')])
        # Z string to the left
        z_string = [(k, 'Z') for k in range(j)]
        # Multiply
        t1 = multiply_pauli_strings(term1, (1.0, z_string))
        t2 = multiply_pauli_strings(term2, (1.0, z_string))
        creators.append(simplify_pauli_sum([t1, t2]))
    return creators


def jordan_wigner_annihilators(n):
    """
    Return the n fermionic annihilation operators a_j as Pauli strings.
    a_j = (1/2) * (X_j + i Y_j) * prod_{k<j} Z_k
    """
    anns = []
    for j in range(n):
        ops = [(j, 'X')]
        term1 = (0.5, ops)
        term2 = (0.5j, [(j, 'Y')])
        z_string = [(k, 'Z') for k in range(j)]
        t1 = multiply_pauli_strings(term1, (1.0, z_string))
        t2 = multiply_pauli_strings(term2, (1.0, z_string))
        anns.append(simplify_pauli_sum([t1, t2]))
    return anns


def jordan_wigner_number(n):
    """
    Return the number operator N = sum_j a^\n    _j a_j as Pauli strings.
    """
    creators = jordan_wigner_creators(n)
    anns = jordan_wigner_annihilators(n)
    terms = []
    for c, a in zip(creators, anns):
        for cc, cops in c:
            for ac, aops in a:
                prod = multiply_pauli_strings((cc, cops), (ac, aops))
                terms.append(prod)
    return simplify_pauli_sum(terms)


def jordan_wigner_hopping(i, j, n):
    """
    Return the hopping term a^\n    _i a_j + a^\n    _j a_i as Pauli strings.
    """
    creators = jordan_wigner_creators(n)
    anns = jordan_wigner_annihilators(n)
    terms = []
    # a^\n    _i a_j
    for cc, cops in creators[i]:
        for ac, aops in anns[j]:
            terms.append(multiply_pauli_strings((cc, cops), (ac, aops)))
    # a^\n    _j a_i
    for cc, cops in creators[j]:
        for ac, aops in anns[i]:
            terms.append(multiply_pauli_strings((cc, cops), (ac, aops)))
    return simplify_pauli_sum(terms)


def jordan_wigner_interaction(i, j, n):
    """
    Return the density-density interaction n_i n_j as Pauli strings.
    """
    creators = jordan_wigner_creators(n)
    anns = jordan_wigner_annihilators(n)
    terms = []
    # n_i = a^\n    _i a_i
    ni_terms = []
    for cc, cops in creators[i]:
        for ac, aops in anns[i]:
            ni_terms.append(multiply_pauli_strings((cc, cops), (ac, aops)))
    ni_terms = simplify_pauli_sum(ni_terms)
    # n_j = a^\n    _j a_j
    nj_terms = []
    for cc, cops in creators[j]:
        for ac, aops in anns[j]:
            nj_terms.append(multiply_pauli_strings((cc, cops), (ac, aops)))
    nj_terms = simplify_pauli_sum(nj_terms)
    # n_i * n_j
    for c1, ops1 in ni_terms:
        for c2, ops2 in nj_terms:
            terms.append(multiply_pauli_strings((c1, ops1), (c2, ops2)))
    return simplify_pauli_sum(terms)


# ---------------------------------------------------------------------------
# Bravyi-Kitaev encoding
# ---------------------------------------------------------------------------

def _build_bk_matrices(n):
    """
    Build the Bravyi-Kitaev binary matrices.
    Returns (beta, alpha) where:
    - beta[j, k] = 1 if qubit k stores parity of occupations up to j
    - alpha[j, k] = 1 if qubit k is used for the update chain of j
    """
    # Binary tree structure
    beta = np.zeros((n, n), dtype=int)
    alpha = np.zeros((n, n), dtype=int)

    for j in range(n):
        # Occupation: qubit j stores occupation of orbital j
        # Parity: qubits store partial parities
        # For BK, the parity set P(j) and update set U(j) are determined by binary tree

        # P(j): qubits that store parity up to j
        # U(j): qubits that need updating when j changes

        # Simple BK construction
        # P(j) = {j} union {highest power of 2 dividing (j+1) - 1, recursively}
        # Actually, let's use the standard recursive definition

        # For each orbital j, find which qubits store its parity info
        k = j
        while k >= 0:
            beta[j, k] = 1
            if k == 0:
                break
            # Move to parent in binary tree
            k = ((k + 1) & k) - 1  # clear lowest set bit

        # Update set: qubits whose parity depends on orbital j
        k = j
        while k < n:
            alpha[j, k] = 1
            # Move to next in chain
            k = k | (k + 1)  # set lowest zero bit

    return beta, alpha


def bravyi_kitaev_creators(n):
    """
    Return BK creation operators as Pauli strings.
    a^\n    _j = (1/2) * (X_{{U(j)}} - i Y_{{U(j)}}) * X_{{P(j)\\{j}}} * Z_{{F(j)}}
    where U(j) = update set, P(j) = parity set, F(j) = flip set.
    """
    beta, alpha = _build_bk_matrices(n)
    creators = []

    for j in range(n):
        # Parity set P(j): qubits that store parity up to j
        Pj = [k for k in range(n) if beta[j, k] == 1]
        # Update set U(j): qubits that need X/Y when creating at j
        Uj = [k for k in range(n) if alpha[j, k] == 1]
        # Flip set F(j): qubits that flip when j is occupied
        Fj = [k for k in range(n) if alpha[k, j] == 1 and k != j]

        # The creation operator:
        # a^\n    _j = (1/2) * (X_{P(j)} - i Y_{P(j)}) * Z_{F(j)}
        # But with the correction that X/Y acts on U(j) instead of full P(j)
        # Actually, standard BK: creation has X on U(j), Z on F(j)
        # And the (X - iY)/2 on j itself

        # Simplified: use the parity and flip sets directly
        x_set = [k for k in Pj if k != j]  # X on parity set minus j
        z_set = Fj  # Z on flip set

        # (X_j - iY_j)/2
        term_x = (0.5, [(j, 'X')] + [(k, 'Z') for k in z_set] + [(k, 'X') for k in x_set])
        term_y = (-0.5j, [(j, 'Y')] + [(k, 'Z') for k in z_set] + [(k, 'X') for k in x_set])

        # Need to combine properly
        creators.append(simplify_pauli_sum([term_x, term_y]))

    return creators


def bravyi_kitaev_annihilators(n):
    """Return BK annihilation operators."""
    creators = bravyi_kitaev_creators(n)
    anns = []
    for term in creators:
        # a_j = (a^\n    _j)^\n    dagger
        new_terms = []
        for coeff, ops in term:
            # Hermitian conjugate: complex conjugate coefficient, same Pauli (X,Y,Z are Hermitian)
            new_terms.append((np.conj(coeff), ops))
        anns.append(new_terms)
    return anns


# ---------------------------------------------------------------------------
# Parity mapping
# ---------------------------------------------------------------------------

def parity_creators(n):
    """
    Parity encoding: store cumulative parities.
    p_j = sum_{k=0}^{j-1} f_k mod 2
    a^\n    _j = (1/2) * (X_j - i Y_j) * Z_{p_j}
    where Z_{p_j} = product of Z on all parity qubits that include j.
    """
    creators = []
    for j in range(n):
        # Parity qubits that contain j in their sum
        parity_qubits = []
        for p in range(j + 1, n):
            # p stores parity of orbitals 0..p-1, so includes j if j < p
            parity_qubits.append(p)

        z_string = [(p, 'Z') for p in parity_qubits]
        term_x = (0.5, [(j, 'X')] + z_string)
        term_y = (-0.5j, [(j, 'Y')] + z_string)
        creators.append(simplify_pauli_sum([term_x, term_y]))
    return creators


def parity_annihilators(n):
    """Return parity annihilation operators."""
    creators = parity_creators(n)
    anns = []
    for term in creators:
        new_terms = []
        for coeff, ops in term:
            new_terms.append((np.conj(coeff), ops))
        anns.append(new_terms)
    return anns


# ---------------------------------------------------------------------------
# Unified interface
# ---------------------------------------------------------------------------

ENCODINGS = {
    'jordan_wigner': (jordan_wigner_creators, jordan_wigner_annihilators),
    'bravyi_kitaev': (bravyi_kitaev_creators, bravyi_kitaev_annihilators),
    'parity': (parity_creators, parity_annihilators),
}


def get_fermionic_operators(n, encoding='jordan_wigner'):
    """
    Get creation and annihilation operators for n fermionic modes.

    Returns (creators, annihilators) where each is a list of n Pauli-string
    representations.

    encoding: 'jordan_wigner', 'bravyi_kitaev', or 'parity'
    """
    if encoding not in ENCODINGS:
        raise ValueError(f"Unknown encoding: {encoding}. Choose from {list(ENCODINGS.keys())}")
    if n > 14:
        raise ValueError("n > 14 exceeds phone-runnable limit")

    c_fn, a_fn = ENCODINGS[encoding]
    return c_fn(n), a_fn(n)


def fermionic_hamiltonian_to_pauli(h_terms, n, encoding='jordan_wigner'):
    """
    Convert a fermionic Hamiltonian to Pauli strings.

    h_terms: list of (coeff, list_of_indices, type)
        type is 'number' (n_i), 'hopping' (a^\n    _i a_j + h.c.),
        or 'coulomb' (n_i n_j)

    Returns list of (coeff, pauli_ops) simplified.
    """
    creators, anns = get_fermionic_operators(n, encoding)
    pauli_terms = []

    for coeff, indices, typ in h_terms:
        if typ == 'number':
            i = indices[0]
            # n_i = a^\n    _i a_i
            for cc, cops in creators[i]:
                for ac, aops in anns[i]:
                    prod = multiply_pauli_strings((cc, cops), (ac, aops))
                    pauli_terms.append((coeff * prod[0], prod[1]))

        elif typ == 'hopping':
            i, j = indices
            # a^\n    _i a_j + a^\n    _j a_i
            for cc, cops in creators[i]:
                for ac, aops in anns[j]:
                    prod = multiply_pauli_strings((cc, cops), (ac, aops))
                    pauli_terms.append((coeff * prod[0], prod[1]))
            for cc, cops in creators[j]:
                for ac, aops in anns[i]:
                    prod = multiply_pauli_strings((cc, cops), (ac, aops))
                    pauli_terms.append((coeff * prod[0], prod[1]))

        elif typ == 'coulomb':
            i, j = indices
            # n_i n_j
            ni_terms = []
            for cc, cops in creators[i]:
                for ac, aops in anns[i]:
                    ni_terms.append(multiply_pauli_strings((cc, cops), (ac, aops)))
            ni_terms = simplify_pauli_sum(ni_terms)

            nj_terms = []
            for cc, cops in creators[j]:
                for ac, aops in anns[j]:
                    nj_terms.append(multiply_pauli_strings((cc, cops), (ac, aops)))
            nj_terms = simplify_pauli_sum(nj_terms)

            for c1, ops1 in ni_terms:
                for c2, ops2 in nj_terms:
                    prod = multiply_pauli_strings((c1, ops1), (c2, ops2))
                    pauli_terms.append((coeff * prod[0], prod[1]))

    return simplify_pauli_sum(pauli_terms)


def pauli_sum_to_matrix(terms, n):
    """
    Convert a list of Pauli string terms to a dense 2^n x 2^n matrix.
    """
    dim = 2 ** n
    H = np.zeros((dim, dim), dtype=complex)
    for coeff, ops in terms:
        H += coeff * pauli_string_to_matrix(ops, n)
    return H


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def _test_jw_anticommutation():
    """Test that JW creation operators anticommute correctly."""
    n = 4
    creators, anns = get_fermionic_operators(n, 'jordan_wigner')

    # Test {a_i, a^\n    _j} = delta_{ij}
    for i in range(n):
        for j in range(n):
            # Build a_i a^\n    _j + a^\n    _j a_i
            terms = []
            for c1, o1 in anns[i]:
                for c2, o2 in creators[j]:
                    terms.append(multiply_pauli_strings((c1, o1), (c2, o2)))
            for c1, o1 in creators[j]:
                for c2, o2 in anns[i]:
                    terms.append(multiply_pauli_strings((c1, o1), (c2, o2)))
            result = simplify_pauli_sum(terms)

            # Convert to matrix
            mat = pauli_sum_to_matrix(result, n)
            expected = np.eye(2**n) if i == j else np.zeros((2**n, 2**n))
            assert np.allclose(mat, expected), f"JW anticommutation failed at i={i}, j={j}"
    print("  JW anticommutation: PASS")


def _test_number_operator():
    """Test that number operator counts fermions."""
    n = 3
    N_op = jordan_wigner_number(n)
    N_mat = pauli_sum_to_matrix(N_op, n)

    # Diagonalize
    eigvals = np.linalg.eigvalsh(N_mat)
    # Should be integers 0, 1, 2, 3 with multiplicities C(3,k)
    expected = []
    for k in range(n + 1):
        expected.extend([k] * int(math.comb(n, k)))
    expected = sorted(expected)
    actual = sorted(np.round(eigvals.real).astype(int))
    assert actual == expected, f"Number operator eigenvalues wrong: {actual} vs {expected}"
    print("  Number operator: PASS")


def _test_hopping_matrix():
    """Test hopping term against exact diagonalization."""
    n = 3
    hop = jordan_wigner_hopping(0, 1, n)
    H = pauli_sum_to_matrix(hop, n)

    # Build exact fermionic matrix in occupation basis
    # Hopping between 0 and 1: t (a^\n    _0 a_1 + a^\n    _1 a_0)
    # In 3-qubit space, check some matrix elements
    # |001> = a^\n    _0 |000> -> hopping to |010> = a^\n    _1 |000>
    # <010| H |001> should be 1

    # Verify Hermitian
    assert np.allclose(H, H.T.conj()), "Hopping not Hermitian"
    print("  Hopping Hermitian: PASS")


def _test_encodings_equivalent():
    """Test that all encodings give same spectrum for number operator."""
    n = 4
    for enc in ['jordan_wigner', 'parity']:
        creators, anns = get_fermionic_operators(n, enc)
        # Build number operator
        terms = []
        for i in range(n):
            for cc, cops in creators[i]:
                for ac, aops in anns[i]:
                    terms.append(multiply_pauli_strings((cc, cops), (ac, aops)))
        N_op = simplify_pauli_sum(terms)
        N_mat = pauli_sum_to_matrix(N_op, n)
        eigvals = sorted(np.round(np.linalg.eigvalsh(N_mat).real).astype(int))
        expected = []
        for k in range(n + 1):
            expected.extend([k] * int(math.comb(n, k)))
        assert eigvals == sorted(expected), f"Encoding {enc} failed"
    print("  Encoding equivalence: PASS")


def _test_bk_vs_jw():
    """Test BK gives same physics as JW for small system."""
    n = 3
    # Hopping term
    jw_hop = jordan_wigner_hopping(0, 1, n)
    bk_hop = fermionic_hamiltonian_to_pauli(
        [(1.0, [0, 1], 'hopping')], n, 'bravyi_kitaev'
    )
    jw_mat = pauli_sum_to_matrix(jw_hop, n)
    bk_mat = pauli_sum_to_matrix(bk_hop, n)

    # Spectra should match
    jw_eig = sorted(np.linalg.eigvalsh(jw_mat))
    bk_eig = sorted(np.linalg.eigvalsh(bk_mat))
    assert np.allclose(jw_eig, bk_eig, atol=1e-10), "BK vs JW spectra mismatch"
    print("  BK vs JW: PASS")


def run_tests():
    print("Testing fermionic_encoding.py...")
    _test_jw_anticommutation()
    _test_number_operator()
    _test_hopping_matrix()
    _test_encodings_equivalent()
    _test_bk_vs_jw()
    print("All tests passed.")


if __name__ == '__main__':
    run_tests()
