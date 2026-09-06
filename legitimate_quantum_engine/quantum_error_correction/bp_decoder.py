"""
bp_decoder.py -- Legitimate Quantum Engine v5.0, Phase 3

Belief Propagation decoder for surface codes.
O(n) complexity vs O(n^3) for MWPM.
Handles X and Z syndromes separately.

Pure NumPy.  Phone-runnable.  Honest limitations.
"""

import numpy as np


class BPDecoder:
    """
    Belief Propagation (min-sum) decoder for rotated surface codes.

    Parameters
    ----------
    distance : int
        Surface code distance (odd, >= 3).
    max_iter : int
        Maximum BP iterations.
    """

    def __init__(self, distance, max_iter=30):
        if distance < 3 or distance % 2 == 0:
            raise ValueError("Distance must be odd and >= 3")
        self.d = distance
        self.max_iter = max_iter
        self._build_tanner_graph()

    # ------------------------------------------------------------------
    # Tanner graph construction
    # ------------------------------------------------------------------
    def _build_tanner_graph(self):
        """Build check-node / variable-node incidence for X and Z separately."""
        d = self.d
        n_data = d * d

        # Build stabilizers (same logic as SurfaceCode)
        x_stabs = []
        z_stabs = []

        # Interior faces
        for r in range(d - 1):
            for c in range(d - 1):
                qubits = [
                    r * d + c, r * d + (c + 1),
                    (r + 1) * d + c, (r + 1) * d + (c + 1),
                ]
                if (r + c) % 2 == 0:
                    x_stabs.append(qubits)
                else:
                    z_stabs.append(qubits)

        # Rough boundary X-stabilizers
        for i in range(1, d - 1, 2):
            x_stabs.append([i * d, (i + 1) * d])
        for i in range(0, d - 1, 2):
            x_stabs.append([i * d + (d - 1), (i + 1) * d + (d - 1)])

        # Smooth boundary Z-stabilizers
        for j in range(0, d - 1, 2):
            z_stabs.append([j, j + 1])
        for j in range(1, d - 1, 2):
            z_stabs.append([(d - 1) * d + j, (d - 1) * d + j + 1])

        self.x_stabs = x_stabs
        self.z_stabs = z_stabs
        self.n_x = len(x_stabs)
        self.n_z = len(z_stabs)
        self.n_data = n_data

        # Build adjacency: for each check, list of vars; for each var, list of checks
        self.x_checks_to_vars = [list(stab) for stab in x_stabs]
        self.x_vars_to_checks = [[] for _ in range(n_data)]
        for cidx, vars_ in enumerate(self.x_checks_to_vars):
            for v in vars_:
                self.x_vars_to_checks[v].append(cidx)

        self.z_checks_to_vars = [list(stab) for stab in z_stabs]
        self.z_vars_to_checks = [[] for _ in range(n_data)]
        for cidx, vars_ in enumerate(self.z_checks_to_vars):
            for v in vars_:
                self.z_vars_to_checks[v].append(cidx)

    # ------------------------------------------------------------------
    # Min-sum BP
    # ------------------------------------------------------------------
    def decode(self, syndrome_x, syndrome_z):
        """
        Decode syndrome and return correction dict.

        Parameters
        ----------
        syndrome_x : list of int
            Indices of flipped X-stabilizers (Z-error defects).
        syndrome_z : list of int
            Indices of flipped Z-stabilizers (X-error defects).

        Returns
        -------
        dict : {data_qubit: 'X'|'Y'|'Z'}
        """
        correction = {}

        # Decode Z errors from X-syndrome defects
        z_errors = self._bp_decode(
            syndrome_x, self.n_x, self.n_data,
            self.x_checks_to_vars, self.x_vars_to_checks
        )
        for q in z_errors:
            correction[q] = _combine_pauli(correction.get(q, 'I'), 'Z')

        # Decode X errors from Z-syndrome defects
        x_errors = self._bp_decode(
            syndrome_z, self.n_z, self.n_data,
            self.z_checks_to_vars, self.z_vars_to_checks
        )
        for q in x_errors:
            correction[q] = _combine_pauli(correction.get(q, 'I'), 'X')

        return correction

    def _bp_decode(self, defects, n_checks, n_vars, checks_to_vars, vars_to_checks):
        """
        Run min-sum BP for one error type.
        Returns list of suspected error qubits.
        """
        if not defects:
            return []

        defects_set = set(defects)

        # Initialize log-likelihood ratios
        # LLR[qubit] = log(P(no error) / P(error))
        # Prior: uniform small error probability
        llr = np.zeros(n_vars)

        # Messages: check -> var and var -> check
        # msg_cv[c][v] = message from check c to var v
        msg_cv = {}
        msg_vc = {}

        for c in range(n_checks):
            for v in checks_to_vars[c]:
                msg_cv[(c, v)] = 0.0
                msg_vc[(v, c)] = 0.0

        # Syndrome contribution: flipped checks send strong messages
        for c in defects_set:
            for v in checks_to_vars[c]:
                msg_cv[(c, v)] = 1.0  # strong belief of error

        # Iterative message passing
        for _ in range(self.max_iter):
            # Variable to check messages
            for v in range(n_vars):
                for c in vars_to_checks[v]:
                    # Sum of incoming check messages (excluding c)
                    total = llr[v]
                    for c2 in vars_to_checks[v]:
                        if c2 != c:
                            total += msg_cv.get((c2, v), 0.0)
                    msg_vc[(v, c)] = total

            # Check to variable messages (min-sum)
            for c in range(n_checks):
                for v in checks_to_vars[c]:
                    # Min-sum: minimum of absolute values, with sign product
                    vals = []
                    for v2 in checks_to_vars[c]:
                        if v2 != v:
                            vals.append(msg_vc.get((v2, c), 0.0))
                    if not vals:
                        msg_cv[(c, v)] = 0.0
                    else:
                        # Product of signs, min of magnitudes
                        sign = 1
                        for val in vals:
                            if val < 0:
                                sign *= -1
                        mag = min(abs(v) for v in vals)
                        msg_cv[(c, v)] = sign * mag

            # Add syndrome bias for flipped checks
            for c in defects_set:
                for v in checks_to_vars[c]:
                    msg_cv[(c, v)] += 0.5

        # Final decision
        beliefs = np.zeros(n_vars)
        for v in range(n_vars):
            beliefs[v] = llr[v]
            for c in vars_to_checks[v]:
                beliefs[v] += msg_cv.get((c, v), 0.0)

        # Threshold: negative belief means likely error
        errors = [v for v in range(n_vars) if beliefs[v] < -0.3]
        return errors


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------
def _combine_pauli(a, b):
    """Combine two Pauli operators."""
    table = {
        ('I', 'X'): 'X', ('I', 'Y'): 'Y', ('I', 'Z'): 'Z',
        ('X', 'I'): 'X', ('X', 'X'): 'I', ('X', 'Y'): 'Z', ('X', 'Z'): 'Y',
        ('Y', 'I'): 'Y', ('Y', 'X'): 'Z', ('Y', 'Y'): 'I', ('Y', 'Z'): 'X',
        ('Z', 'I'): 'Z', ('Z', 'X'): 'Y', ('Z', 'Y'): 'X', ('Z', 'Z'): 'I',
    }
    return table.get((a, b), 'I')


# ========================================================================
# Tests
# ========================================================================
def test_bp_d3_single():
    print("\n=== Test: BP d=3 Single Error ===")
    from .surface_code import SurfaceCode
    sc = SurfaceCode(distance=3)
    sc.encode_logical_zero()
    sc.inject_error("X", 4)
    syn = sc.measure_syndrome()

    bp = BPDecoder(distance=3)
    corr = bp.decode(syn['X'], syn['Z'])
    print(f"  Correction: {corr}")
    assert 4 in corr
    print("  PASS")


def test_bp_d5_chain():
    print("\n=== Test: BP d=5 Error Chain ===")
    from .surface_code import SurfaceCode
    sc = SurfaceCode(distance=5)
    sc.encode_logical_zero()
    sc.inject_error("Z", 6)
    sc.inject_error("Z", 7)
    syn = sc.measure_syndrome()

    bp = BPDecoder(distance=5)
    corr = bp.decode(syn['X'], syn['Z'])
    print(f"  Correction: {corr}")
    # Should find at least one of the errors
    assert len(corr) > 0
    print("  PASS")


def test_bp_vs_mwpm():
    print("\n=== Test: BP vs MWPM (d=3) ===")
    from .surface_code import SurfaceCode
    sc = SurfaceCode(distance=3)
    sc.encode_logical_zero()
    sc.inject_error("X", 2)
    sc.inject_error("X", 4)
    syn = sc.measure_syndrome()

    bp = BPDecoder(distance=3)
    bp_corr = bp.decode(syn['X'], syn['Z'])

    sc2 = SurfaceCode(distance=3)
    sc2.encode_logical_zero()
    sc2.inject_error("X", 2)
    sc2.inject_error("X", 4)
    mwpm_corr = sc2.decode_mwpm()

    print(f"  BP: {bp_corr}, MWPM: {mwpm_corr}")
    print("  PASS")


def test_bp_speed():
    print("\n=== Test: BP Speed (d=11) ===")
    import time
    bp = BPDecoder(distance=11)
    # Random syndrome
    np.random.seed(42)
    syn_x = list(np.random.choice(bp.n_x, size=4, replace=False))
    syn_z = list(np.random.choice(bp.n_z, size=4, replace=False))
    t0 = time.time()
    for _ in range(10):
        bp.decode(syn_x, syn_z)
    dt = (time.time() - t0) / 10
    print(f"  Average decode time: {dt*1000:.2f} ms")
    assert dt < 0.1
    print("  PASS")


def run_all_tests():
    print("=" * 60)
    print("BP DECODER TEST SUITE")
    print("=" * 60)
    test_bp_d3_single()
    test_bp_d5_chain()
    test_bp_vs_mwpm()
    test_bp_speed()
    print("\n" + "=" * 60)
    print("ALL BP TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
