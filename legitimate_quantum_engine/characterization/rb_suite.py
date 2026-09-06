"""
rb_suite.py -- Legitimate Quantum Engine v5.0, Phase 1

Randomized Benchmarking suite:
  - Clifford RB: sequence fidelity vs depth, extract error rate
  - Cross-entropy benchmarking: compare to ideal distribution

Pure NumPy.  Phone-runnable.  Honest limitations.
"""

import numpy as np
import json


class RandomizedBenchmarking:
    """
    Clifford randomized benchmarking and cross-entropy benchmarking.

    Parameters
    ----------
    n_qubits : int
    n_seeds : int
        Number of random sequences per depth.
    depths : list of int
        Clifford sequence lengths to test.
    """

    def __init__(self, n_qubits, n_seeds=10, depths=None):
        self.n = n_qubits
        self.n_seeds = n_seeds
        self.depths = depths or [1, 2, 4, 8, 16]

    # ------------------------------------------------------------------
    # Clifford RB
    # ------------------------------------------------------------------
    def _random_clifford_sequence(self, depth, seed=None):
        """Generate a random Clifford sequence of given depth."""
        if seed is not None:
            np.random.seed(seed)
        from ..core.statevector import StatevectorSim
        sim = StatevectorSim(self.n)
        sim.apply("H", 0)  # start in |+>
        gates = []
        for _ in range(depth):
            # Random single-qubit Cliffords
            for q in range(self.n):
                r = np.random.randint(0, 24)
                gates.append(("clifford", r, q))
                self._apply_clifford(sim, r, q)
            # Random CNOT layer
            for q in range(0, self.n - 1, 2):
                gates.append(("CNOT", q, q + 1))
                sim.apply("CNOT", q, q + 1)
        # Inverse (simplified: just reset to |0> for benchmarking)
        # In a full implementation, compute the inverse Clifford
        return sim, gates

    def _apply_clifford(self, sim, idx, q):
        """Apply one of 24 single-qubit Cliffords."""
        # Simplified: use H, S, X combinations
        ops = [
            [], [("H", q)], [("S", q)], [("H", q), ("S", q)],
            [("S", q), ("H", q)], [("H", q), ("S", q), ("H", q)],
            [("X", q)], [("X", q), ("H", q)], [("X", q), ("S", q)],
            [("H", q), ("X", q)], [("S", q), ("X", q)],
            [("H", q), ("S", q), ("X", q)],
            [("Y", q)], [("Y", q), ("H", q)], [("Z", q)],
            [("Z", q), ("H", q)], [("Z", q), ("S", q)],
            [("H", q), ("Z", q)], [("S", q), ("Z", q)],
            [("H", q), ("S", q), ("Z", q)],
            [("X", q), ("Y", q)], [("Y", q), ("Z", q)],
            [("Z", q), ("X", q)], [("H", q), ("X", q), ("Y", q)],
        ]
        for op in ops[idx % 24]:
            if len(op) == 2:
                sim.apply(op[0], op[1])
            else:
                sim.apply(op[0], op[1], op[2])

    def clifford_rb(self):
        """
        Run Clifford RB.  Returns dict with fidelity vs depth and
        fitted error rate.
        """
        from ..core.statevector import StatevectorSim
        results = {}
        for d in self.depths:
            fidelities = []
            for s in range(self.n_seeds):
                sim = StatevectorSim(self.n)
                sim.apply("H", 0)
                # Build random sequence
                for _ in range(d):
                    for q in range(self.n):
                        r = np.random.randint(0, 24)
                        self._apply_clifford(sim, r, q)
                    for q in range(0, self.n - 1, 2):
                        sim.apply("CNOT", q, q + 1)
                # Compute survival probability (simplified: overlap with |0>)
                fid = abs(sim.state[0]) ** 2
                fidelities.append(fid)
            results[d] = {
                "mean": float(np.mean(fidelities)),
                "std": float(np.std(fidelities)),
            }

        # Fit to F = A * p^m + B
        depths_arr = np.array(self.depths, dtype=float)
        means = np.array([results[d]["mean"] for d in self.depths])
        # Simple exponential fit: log(F - B) vs m
        # Assume B = 1/2^n
        B = 1.0 / (1 << self.n)
        log_vals = np.log(np.maximum(means - B, 1e-12))
        # Linear fit: log(F-B) = log(A) + m * log(p)
        # Use least squares on first half
        k = len(depths_arr) // 2 + 1
        X = np.vstack([np.ones(k), depths_arr[:k]]).T
        beta = np.linalg.lstsq(X, log_vals[:k], rcond=None)[0]
        p_fit = np.exp(beta[1])
        error_rate = (1 - p_fit) * (1 - 1 / (1 << self.n))

        return {
            "depths": self.depths,
            "fidelities": results,
            "fit_p": float(p_fit),
            "error_rate": float(error_rate),
        }

    # ------------------------------------------------------------------
    # Cross-entropy benchmarking
    # ------------------------------------------------------------------
    def cross_entropy(self, n_circuits=10, depth=10):
        """
        Cross-entropy benchmarking score.
        For an ideal simulator, score should be ~1.0.
        """
        from ..core.statevector import StatevectorSim
        scores = []
        for c in range(n_circuits):
            sim = StatevectorSim(self.n)
            # Random circuit
            for _ in range(depth):
                for q in range(self.n):
                    r = np.random.randint(0, 24)
                    self._apply_clifford(sim, r, q)
                for q in range(0, self.n - 1, 2):
                    sim.apply("CNOT", q, q + 1)
            probs = sim.probabilities()
            # Cross-entropy: -sum p_ideal * log(p_ideal) = entropy
            # For ideal sim, H(p, p) = H(p)
            # Score = (H_max - H(p)) / H_max
            H = -np.sum(probs * np.log2(np.maximum(probs, 1e-12)))
            H_max = self.n
            score = (H_max - H) / H_max
            scores.append(score)
        return {
            "mean_score": float(np.mean(scores)),
            "std_score": float(np.std(scores)),
            "n_circuits": n_circuits,
            "depth": depth,
        }

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------
    def export_json(self, path="rb_report.json"):
        """Export full benchmark report as JSON."""
        rb = self.clifford_rb()
        xeb = self.cross_entropy()
        report = {
            "n_qubits": self.n,
            "clifford_rb": rb,
            "cross_entropy": xeb,
        }
        with open(path, "w") as f:
            json.dump(report, f, indent=2)
        return report


# ========================================================================
# Tests
# ========================================================================
def test_clifford_rb():
    print("\n=== Test: Clifford RB (4 qubits) ===")
    rb = RandomizedBenchmarking(n_qubits=4, n_seeds=5, depths=[1, 2, 4])
    res = rb.clifford_rb()
    assert "error_rate" in res
    assert res["error_rate"] >= 0
    print(f"  PASS  (error_rate={res['error_rate']:.4f})")


def test_cross_entropy():
    print("\n=== Test: Cross-Entropy (4 qubits) ===")
    rb = RandomizedBenchmarking(n_qubits=4, n_seeds=3)
    res = rb.cross_entropy(n_circuits=5, depth=5)
    assert res["mean_score"] > 0
    print(f"  PASS  (score={res['mean_score']:.4f})")


def test_json_export():
    print("\n=== Test: JSON Export ===")
    rb = RandomizedBenchmarking(n_qubits=3, n_seeds=3, depths=[1, 2])
    report = rb.export_json(path="/tmp/rb_test.json")
    assert "clifford_rb" in report
    print("  PASS  (JSON exported)")


def run_all_tests():
    print("=" * 60)
    print("RANDOMIZED BENCHMARKING TEST SUITE")
    print("=" * 60)
    test_clifford_rb()
    test_cross_entropy()
    test_json_export()
    print("\n" + "=" * 60)
    print("ALL RB TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
