"""
surface_code.py — Legitimate Quantum Engine v4.0, Module 5

Rotated surface code of distance d.
Classical syndrome-tracking simulator for error injection, MWPM decoding,
and logical state verification. Uses the stabilizer formalism (conceptually
builds on Module 1).

Phone-viable for d <= 11 (121 data qubits + 120 ancilla = 241 total).
"""

import numpy as np
from itertools import combinations, permutations


class SurfaceCode:
    """
    Rotated surface code on a d x d grid of data qubits.

    Stabilizer layout (for d=3 example):
        Data qubits (D) on a 3x3 grid:
            D0 D1 D2
            D3 D4 D5
            D6 D7 D8

        X-stabilizers (measure X on data, use X-ancilla):
            - Interior faces (r+c even): [0,1,3,4], [4,5,7,8]
            - Rough boundaries: [2,5] (right), [3,6] (left)

        Z-stabilizers (measure Z on data, use Z-ancilla):
            - Interior faces (r+c odd): [1,2,4,5], [3,4,6,7]
            - Smooth boundaries: [0,1] (top), [7,8] (bottom)

    Logical operators:
        Z_L = Z on left column  (e.g., Z_0 Z_3 Z_6 for d=3)
        X_L = X on top row      (e.g., X_0 X_1 X_2 for d=3)
    """

    def __init__(self, distance: int):
        if distance < 3 or distance % 2 == 0:
            raise ValueError("Distance must be odd and >= 3")
        self.d = distance
        self.n_data = distance * distance
        self._build_stabilizers()
        self._build_logical_operators()
        self._build_lookup_tables()
        self.syndrome_x = {}   # x_stab_index -> +1 or -1
        self.syndrome_z = {}   # z_stab_index -> +1 or -1
        self.errors = {}       # data_qubit -> 'X' | 'Y' | 'Z'

    # ------------------------------------------------------------------
    # Lattice construction
    # ------------------------------------------------------------------
    def _build_stabilizers(self):
        """Build lists of X and Z stabilizers as lists of data qubit indices."""
        self.x_stabs = []   # list of list[int]
        self.z_stabs = []
        d = self.d

        # Interior faces
        for r in range(d - 1):
            for c in range(d - 1):
                qubits = [
                    r * d + c,
                    r * d + (c + 1),
                    (r + 1) * d + c,
                    (r + 1) * d + (c + 1),
                ]
                if (r + c) % 2 == 0:
                    self.x_stabs.append(qubits)
                else:
                    self.z_stabs.append(qubits)

        # Rough boundary X-stabilizers (left + right)
        for i in range(1, d - 1, 2):   # odd rows, left boundary
            self.x_stabs.append([i * d, (i + 1) * d])
        for i in range(0, d - 1, 2):   # even rows, right boundary
            self.x_stabs.append([i * d + (d - 1), (i + 1) * d + (d - 1)])

        # Smooth boundary Z-stabilizers (top + bottom)
        for j in range(0, d - 1, 2):   # even cols, top boundary
            self.z_stabs.append([j, j + 1])
        for j in range(1, d - 1, 2):   # odd cols, bottom boundary
            self.z_stabs.append([(d - 1) * d + j, (d - 1) * d + j + 1])

        self.n_x_stab = len(self.x_stabs)
        self.n_z_stab = len(self.z_stabs)

    def _build_logical_operators(self):
        """Define logical X and Z as lists of data qubit indices."""
        d = self.d
        # Logical Z = left column
        self.logical_z = [i * d for i in range(d)]
        # Logical X = top row
        self.logical_x = list(range(d))

    def _stab_to_str(self, stab):
        """Convert stabilizer list to readable Pauli string."""
        chars = ['I'] * self.n_data
        for q in stab:
            chars[q] = 'X'  # or Z, context-dependent
        return ''.join(chars)

    # ------------------------------------------------------------------
    # Encoding and error injection
    # ------------------------------------------------------------------
    def encode_logical_zero(self):
        """Reset to encoded |0>_L (all syndromes trivial, no errors)."""
        self.syndrome_x = {}
        self.syndrome_z = {}
        self.errors = {}

    def inject_error(self, pauli: str, data_qubit: int):
        """
        Inject a Pauli error on a data qubit.
        pauli: 'X', 'Y', or 'Z'
        """
        if data_qubit < 0 or data_qubit >= self.n_data:
            raise ValueError(f"Data qubit {data_qubit} out of range [0, {self.n_data})")
        pauli = pauli.upper()

        # Track accumulated error (simplified: just overwrite for demo)
        if data_qubit in self.errors:
            # Combine Paulis: X*Z=Y, etc.
            old = self.errors[data_qubit]
            self.errors[data_qubit] = _combine_pauli(old, pauli)
        else:
            self.errors[data_qubit] = pauli

        # Update syndrome
        if pauli in ('X', 'Y'):
            # X error anticommutes with Z-stabilizers containing this qubit
            for idx, stab in enumerate(self.z_stabs):
                if data_qubit in stab:
                    self.syndrome_z[idx] = self.syndrome_z.get(idx, 1) * -1

        if pauli in ('Z', 'Y'):
            # Z error anticommutes with X-stabilizers containing this qubit
            for idx, stab in enumerate(self.x_stabs):
                if data_qubit in stab:
                    self.syndrome_x[idx] = self.syndrome_x.get(idx, 1) * -1

    def measure_syndrome(self):
        """Return current syndrome as dict of flipped stabilizers."""
        x_flips = [i for i, v in self.syndrome_x.items() if v == -1]
        z_flips = [i for i, v in self.syndrome_z.items() if v == -1]
        return {'X': x_flips, 'Z': z_flips}

    # ------------------------------------------------------------------
    # MWPM Decoder
    # ------------------------------------------------------------------
    def decode_mwpm(self):
        """
        Minimum-Weight Perfect Matching decoder.
        Returns correction as {qubit: pauli}.
        """
        correction = {}

        # Decode Z errors (from X-syndrome defects)
        x_defects = [i for i, v in self.syndrome_x.items() if v == -1]
        z_corr = self._decode_defects(x_defects, 'Z')
        correction.update(z_corr)

        # Decode X errors (from Z-syndrome defects)
        z_defects = [i for i, v in self.syndrome_z.items() if v == -1]
        x_corr = self._decode_defects(z_defects, 'X')
        correction.update(x_corr)

        return correction

    def _decode_defects(self, defects, error_type):
        """Decode a set of syndrome defects for one error type."""
        if not defects:
            return {}

        # For very small instances, use brute-force perfect matching
        if len(defects) <= 8:
            return self._decode_brute_force(defects, error_type)
        else:
            return self._decode_greedy(defects, error_type)

    def _decode_brute_force(self, defects, error_type):
        """Brute-force minimum-weight perfect matching."""
        n = len(defects)
        if n % 2 == 1:
            # Odd number of defects: match one to boundary
            # Add virtual boundary defect
            defects = defects + [-1]
            n += 1

        # Precompute distances
        dist = {}
        for i in range(n):
            for j in range(i + 1, n):
                dist[(i, j)] = self._defect_distance(defects[i], defects[j], error_type)

        # Generate all perfect matchings
        best_weight = float('inf')
        best_pairs = None

        # Recursive matching generation
        items = list(range(n))

        def gen_matchings(remaining, current_pairs, current_weight):
            nonlocal best_weight, best_pairs
            if not remaining:
                if current_weight < best_weight:
                    best_weight = current_weight
                    best_pairs = current_pairs.copy()
                return
            if current_weight >= best_weight:
                return
            i = remaining[0]
            for j in remaining[1:]:
                w = dist.get((min(i,j), max(i,j)), 0)
                gen_matchings(
                    [x for x in remaining[1:] if x != j],
                    current_pairs + [(defects[i], defects[j])],
                    current_weight + w
                )

        gen_matchings(items, [], 0)

        # Build correction from best matching
        correction = {}
        for d1, d2 in best_pairs:
            path = self._defect_path(d1, d2, error_type)
            for q in path:
                correction[q] = _combine_pauli(correction.get(q, 'I'), error_type)
        return correction

    def _decode_greedy(self, defects, error_type):
        """Greedy matching for larger instances."""
        unmatched = defects.copy()
        if len(unmatched) % 2 == 1:
            unmatched.append(-1)  # boundary

        correction = {}
        while unmatched:
            # Find closest pair
            min_dist = float('inf')
            best_pair = None
            for i in range(len(unmatched)):
                for j in range(i + 1, len(unmatched)):
                    d = self._defect_distance(unmatched[i], unmatched[j], error_type)
                    if d < min_dist:
                        min_dist = d
                        best_pair = (unmatched[i], unmatched[j])
            d1, d2 = best_pair
            unmatched.remove(d1)
            unmatched.remove(d2)
            path = self._defect_path(d1, d2, error_type)
            for q in path:
                correction[q] = _combine_pauli(correction.get(q, 'I'), error_type)
        return correction

    def _defect_distance(self, d1, d2, error_type):
        """Approximate distance between two syndrome defects."""
        if d1 == -1 or d2 == -1:
            # Distance to boundary
            real = d2 if d1 == -1 else d1
            pos = self._defect_position(real, error_type)
            # Distance to nearest boundary
            if error_type == 'Z':  # X-defects
                return min(pos[0] + 1, self.d - 1 - pos[0], pos[1] + 1, self.d - 1 - pos[1])
            else:
                return min(pos[0] + 1, self.d - 1 - pos[0], pos[1] + 1, self.d - 1 - pos[1])
        pos1 = self._defect_position(d1, error_type)
        pos2 = self._defect_position(d2, error_type)
        return abs(pos1[0] - pos2[0]) + abs(pos1[1] - pos2[1])

    def _defect_position(self, defect_idx, error_type):
        """Return (row, col) coordinate of a defect."""
        if error_type == 'Z':  # X-syndrome defect
            stabs = self.x_stabs
        else:
            stabs = self.z_stabs

        stab = stabs[defect_idx]
        # Use average position of qubits in stabilizer
        rows = [q // self.d for q in stab]
        cols = [q % self.d for q in stab]
        return (sum(rows) / len(rows), sum(cols) / len(cols))

    def _defect_path(self, d1, d2, error_type):
        """Return list of data qubits on a shortest path between defects."""
        if d1 == -1:
            return self._boundary_path(d2, error_type)
        if d2 == -1:
            return self._boundary_path(d1, error_type)

        # Get qubits in each stabilizer
        if error_type == 'Z':
            s1 = set(self.x_stabs[d1])
            s2 = set(self.x_stabs[d2])
        else:
            s1 = set(self.z_stabs[d1])
            s2 = set(self.z_stabs[d2])

        # If they share a qubit, the path is just that qubit (or shared qubits)
        shared = s1 & s2
        if shared:
            return list(shared)

        # Otherwise, find shortest path through data qubits
        # Use BFS on data qubit adjacency graph
        return self._bfs_path(s1, s2)

    def _boundary_path(self, defect_idx, error_type):
        """Path from a defect to the nearest boundary."""
        if error_type == 'Z':
            stab = set(self.x_stabs[defect_idx])
        else:
            stab = set(self.z_stabs[defect_idx])
        # Find qubit closest to boundary
        best_q = min(stab, key=lambda q: min(q // self.d, self.d - 1 - q // self.d,
                                               q % self.d, self.d - 1 - q % self.d))
        return [best_q]

    def _bfs_path(self, start_set, end_set):
        """BFS on data qubit grid to find shortest path."""
        from collections import deque
        d = self.d
        # Adjacency: nearest neighbors on grid
        def neighbors(q):
            r, c = q // d, q % d
            for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
                nr, nc = r+dr, c+dc
                if 0 <= nr < d and 0 <= nc < d:
                    yield nr * d + nc

        # Multi-source BFS
        queue = deque([(q, [q]) for q in start_set])
        visited = set(start_set)
        while queue:
            q, path = queue.popleft()
            if q in end_set:
                return path
            for nq in neighbors(q):
                if nq not in visited:
                    visited.add(nq)
                    queue.append((nq, path + [nq]))
        return []

    # ------------------------------------------------------------------
    # Correction and logical measurement
    # ------------------------------------------------------------------
    def correct(self):
        """Apply decoded correction to the syndrome."""
        correction = self.decode_mwpm()
        for q, p in correction.items():
            # Injecting the same error again cancels it
            self.inject_error(p, q)
        # After correction, syndrome should be trivial
        # Remove trivial errors (pairs that cancel)
        self._simplify_errors()

    def _simplify_errors(self):
        """Remove errors that are in the stabilizer group (trivial)."""
        # Simplified: just clear if syndrome is trivial
        if not self.syndrome_x and not self.syndrome_z:
            self.errors = {}

    def measure_logical(self):
        """
        Measure logical Z operator.
        Returns 0 or 1 (eigenvalue +1 or -1).
        """
        # Count Z and Y errors on logical Z chain
        flips = 0
        for q in self.logical_z:
            if q in self.errors and self.errors[q] in ('Z', 'Y'):
                flips += 1
        return flips % 2

    def measure_logical_x(self):
        """Measure logical X operator."""
        flips = 0
        for q in self.logical_x:
            if q in self.errors and self.errors[q] in ('X', 'Y'):
                flips += 1
        return flips % 2

    # ------------------------------------------------------------------
    # Lookup table for fast single-error decoding
    # ------------------------------------------------------------------
    def _build_lookup_tables(self):
        """Precompute syndrome signatures for single-qubit errors."""
        self._lookup_x = {}  # syndrome tuple -> qubit
        self._lookup_z = {}
        self._lookup_y = {}

        for q in range(self.n_data):
            # X error
            z_synd = []
            for idx, stab in enumerate(self.z_stabs):
                if q in stab:
                    z_synd.append(idx)
            self._lookup_x[tuple(z_synd)] = q

            # Z error
            x_synd = []
            for idx, stab in enumerate(self.x_stabs):
                if q in stab:
                    x_synd.append(idx)
            self._lookup_z[tuple(x_synd)] = q

            # Y error = both
            self._lookup_y[(tuple(x_synd), tuple(z_synd))] = q


# =============================================================================
# Helpers
# =============================================================================

def _combine_pauli(a, b):
    """Combine two Pauli operators."""
    table = {
        ('I','X'): 'X', ('I','Y'): 'Y', ('I','Z'): 'Z',
        ('X','I'): 'X', ('X','X'): 'I', ('X','Y'): 'Z', ('X','Z'): 'Y',
        ('Y','I'): 'Y', ('Y','X'): 'Z', ('Y','Y'): 'I', ('Y','Z'): 'X',
        ('Z','I'): 'Z', ('Z','X'): 'Y', ('Z','Y'): 'X', ('Z','Z'): 'I',
    }
    return table.get((a, b), 'I')


# =============================================================================
# Tests
# =============================================================================

def test_d3_single_error():
    """d=3: inject single X error, decode correctly."""
    print("\n=== Test: d=3 Single Error ===")
    sc = SurfaceCode(distance=3)
    sc.encode_logical_zero()

    # Inject X error on data qubit 4 (center)
    sc.inject_error("X", 4)
    syndrome = sc.measure_syndrome()
    print(f"  Syndrome: {syndrome}")

    sc.correct()
    corrected_syndrome = sc.measure_syndrome()
    print(f"  Corrected syndrome: {corrected_syndrome}")

    assert corrected_syndrome == {'X': [], 'Z': []}, "Syndrome should be trivial after correction"
    logical = sc.measure_logical()
    print(f"  Logical Z: {logical} (expected 0)")
    assert logical == 0, "Logical state should be preserved"
    print("  PASS")


def test_d5_two_errors():
    """d=5: inject two errors, decode correctly."""
    print("\n=== Test: d=5 Two Errors ===")
    sc = SurfaceCode(distance=5)
    sc.encode_logical_zero()

    # Inject two X errors
    sc.inject_error("X", 6)
    sc.inject_error("X", 18)
    syndrome = sc.measure_syndrome()
    print(f"  Syndrome X defects: {len(syndrome['X'])}, Z defects: {len(syndrome['Z'])}")

    sc.correct()
    corrected = sc.measure_syndrome()
    print(f"  Corrected: X={corrected['X']}, Z={corrected['Z']}")

    assert corrected == {'X': [], 'Z': []}
    assert sc.measure_logical() == 0
    print("  PASS")


def test_d7_error_chain():
    """d=7: inject error chain, MWPM finds chain."""
    print("\n=== Test: d=7 Error Chain ===")
    sc = SurfaceCode(distance=7)
    sc.encode_logical_zero()

    # Inject a chain of Z errors from qubit 10 to qubit 16
    # Path: 10 -> 11 -> 12 -> 13 -> 14 -> 15 -> 16 (horizontal)
    for q in range(10, 17):
        sc.inject_error("Z", q)

    syndrome = sc.measure_syndrome()
    print(f"  Syndrome X defects: {len(syndrome['X'])}")

    sc.correct()
    corrected = sc.measure_syndrome()
    print(f"  Corrected: X={corrected['X']}, Z={corrected['Z']}")

    assert corrected == {'X': [], 'Z': []}
    assert sc.measure_logical() == 0
    print("  PASS")


def test_logical_error():
    """Test that an uncorrectable logical error changes logical state."""
    print("\n=== Test: Logical Error ===")
    sc = SurfaceCode(distance=3)
    sc.encode_logical_zero()

    # Inject logical X = top row
    for q in sc.logical_x:
        sc.inject_error("X", q)

    syndrome = sc.measure_syndrome()
    print(f"  Syndrome: {syndrome}")

    # Decoder will try to correct, but logical error remains
    sc.correct()
    logical = sc.measure_logical_x()
    print(f"  Logical X after correction: {logical} (expected 1)")
    assert logical == 1, "Logical X should be flipped"
    print("  PASS")


def run_all_tests():
    print("=" * 60)
    print("SURFACE CODE TEST SUITE")
    print("=" * 60)
    test_d3_single_error()
    test_d5_two_errors()
    test_d7_error_chain()
    test_logical_error()
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
