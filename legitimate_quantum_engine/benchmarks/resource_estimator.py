"""
resource_estimator.py -- Legitimate Quantum Engine v5.0, Phase 1

Circuit feasibility checker.  Input = circuit or algorithm description.
Output = estimated qubits, depth, T-count, error budget, runtime on
current hardware.  Compares against IBM, Google, IonQ specs.

Pure NumPy.  Phone-runnable.  Honest limitations.
"""

import numpy as np


# ------------------------------------------------------------------
# Hardware specs (hardcoded, user-suppliable)
# ------------------------------------------------------------------
_DEFAULT_HARDWARE = {
    "ibm_eagle": {
        "qubits": 127,
        "two_qubit_error": 1e-3,
        "t_gate_error": 1e-3,
        "t_gate_time_ns": 100,
        "two_qubit_time_ns": 500,
        "connectivity": "heavy_hex",
    },
    "ibm_heron": {
        "qubits": 133,
        "two_qubit_error": 5e-4,
        "t_gate_error": 5e-4,
        "t_gate_time_ns": 80,
        "two_qubit_time_ns": 400,
        "connectivity": "heavy_hex",
    },
    "google_sycamore": {
        "qubits": 70,
        "two_qubit_error": 5e-3,
        "t_gate_error": 1e-3,
        "t_gate_time_ns": 15,
        "two_qubit_time_ns": 30,
        "connectivity": "grid",
    },
    "ionq_forte": {
        "qubits": 36,
        "two_qubit_error": 1e-2,
        "t_gate_error": 1e-2,
        "t_gate_time_ns": 10000,
        "two_qubit_time_ns": 10000,
        "connectivity": "all_to_all",
    },
}


class ResourceEstimator:
    """
    Analyze a quantum circuit and report resource requirements
    versus available hardware.

    Parameters
    ----------
    circuit : list of tuples
        Each tuple is (gate_name, *args).
        e.g. [("H", 0), ("CNOT", 0, 1), ("RZ", 0.5, 2)]
    hardware : str or dict
        Either a key from _DEFAULT_HARDWARE or a custom dict.
    """

    def __init__(self, circuit, hardware="ibm_eagle"):
        self.circuit = circuit
        if isinstance(hardware, str):
            self.hw = _DEFAULT_HARDWARE.get(hardware, _DEFAULT_HARDWARE["ibm_eagle"]).copy()
        else:
            self.hw = hardware.copy()

    # ------------------------------------------------------------------
    # Analysis
    # ------------------------------------------------------------------
    def analyze(self):
        """Return full resource report as a dict."""
        n_qubits = self._count_qubits()
        depth = self._estimate_depth()
        t_count = self._count_t_gates()
        two_q_count = self._count_two_qubit_gates()
        total_gates = len(self.circuit)

        # Error budget (simplified: multiply gate errors)
        p_t = self.hw["t_gate_error"]
        p_2q = self.hw["two_qubit_error"]
        # Approximate total error from independent gate errors
        total_error = 1 - (1 - p_t) ** t_count * (1 - p_2q) ** two_q_count

        # Runtime estimate (ns -> us -> ms -> s)
        t_time = self.hw["t_gate_time_ns"]
        two_q_time = self.hw["two_qubit_time_ns"]
        # Assume sequential execution at depth, parallel within each layer
        runtime_ns = depth * max(t_time, two_q_time)
        runtime_s = runtime_ns * 1e-9

        # Feasibility
        feasible = (
            n_qubits <= self.hw["qubits"]
            and total_error < 0.5   # arbitrary threshold
        )

        # Bottleneck
        if n_qubits > self.hw["qubits"]:
            bottleneck = "qubit_count"
        elif total_error > 0.5:
            bottleneck = "error_rate"
        elif depth > 1e6:
            bottleneck = "depth"
        else:
            bottleneck = "none"

        return {
            "feasible": feasible,
            "bottleneck": bottleneck,
            "qubits_required": n_qubits,
            "qubits_available": self.hw["qubits"],
            "depth": depth,
            "total_gates": total_gates,
            "t_count": t_count,
            "two_qubit_count": two_q_count,
            "estimated_error": total_error,
            "estimated_runtime_s": runtime_s,
            "hardware": self.hw,
        }

    def _count_qubits(self):
        """Maximum qubit index + 1."""
        max_q = 0
        for gate in self.circuit:
            for arg in gate[1:]:
                if isinstance(arg, int):
                    max_q = max(max_q, arg)
        return max_q + 1

    def _estimate_depth(self):
        """
        Greedy scheduling: assign each gate to the earliest layer
        where all its qubits are free.
        """
        # layer_end[qubit] = layer index when qubit becomes free
        layer_end = {}
        current_depth = 0
        for gate in self.circuit:
            qubits = [arg for arg in gate[1:] if isinstance(arg, int)]
            if not qubits:
                continue
            earliest = max(layer_end.get(q, 0) for q in qubits)
            for q in qubits:
                layer_end[q] = earliest + 1
            current_depth = max(current_depth, earliest + 1)
        return current_depth

    def _count_t_gates(self):
        """Count T, Tdag, and RZ gates (approximate T-count)."""
        count = 0
        for gate in self.circuit:
            name = gate[0].upper()
            if name in ("T", "TDG", "TDAG", "RZ"):
                count += 1
        return count

    def _count_two_qubit_gates(self):
        """Count CNOT, CZ, SWAP, etc."""
        count = 0
        for gate in self.circuit:
            name = gate[0].upper()
            if name in ("CNOT", "CZ", "SWAP", "ISWAP", "CPHASE"):
                count += 1
        return count

    # ------------------------------------------------------------------
    # Convenience
    # ------------------------------------------------------------------
    def print_report(self):
        r = self.analyze()
        print("=" * 50)
        print("RESOURCE ESTIMATION REPORT")
        print("=" * 50)
        print(f"  Feasible:        {r['feasible']}")
        print(f"  Bottleneck:      {r['bottleneck']}")
        print(f"  Qubits needed:   {r['qubits_required']}")
        print(f"  Qubits available:{r['qubits_available']}")
        print(f"  Circuit depth:   {r['depth']}")
        print(f"  Total gates:     {r['total_gates']}")
        print(f"  T-count:         {r['t_count']}")
        print(f"  2-qubit gates:   {r['two_qubit_count']}")
        print(f"  Est. error:      {r['estimated_error']:.4f}")
        print(f"  Est. runtime:    {r['estimated_runtime_s']:.4e} s")
        print("=" * 50)


# ========================================================================
# Tests
# ========================================================================
def test_shor_15():
    print("\n=== Test: Shor\'s 15 ===")
    # Toy Shor circuit: ~12 qubits, moderate depth
    circ = [("H", i) for i in range(8)]
    circ += [("CNOT", i, i + 4) for i in range(4)]
    circ += [("RZ", 0.5, i) for i in range(8)]
    est = ResourceEstimator(circ, hardware="ibm_eagle")
    r = est.analyze()
    assert r["feasible"] is True
    assert r["qubits_required"] <= 127
    print(f"  PASS  (feasible={r['feasible']}, qubits={r['qubits_required']})")


def test_50q_vqe():
    print("\n=== Test: 50-qubit VQE ===")
    circ = [("RY", 0.1, i) for i in range(50)]
    circ += [("CNOT", i, i + 1) for i in range(49)]
    est = ResourceEstimator(circ, hardware="ibm_eagle")
    r = est.analyze()
    assert r["feasible"] is True   # Eagle has 127 qubits
    assert r["bottleneck"] == "none"
    print(f"  PASS  (feasible={r['feasible']}, bottleneck={r['bottleneck']})")


def test_1000q_infeasible():
    print("\n=== Test: 1000-qubit algorithm ===")
    circ = [("H", i) for i in range(1000)]
    circ += [("CNOT", i, (i + 1) % 1000) for i in range(1000)]
    est = ResourceEstimator(circ, hardware="ibm_eagle")
    r = est.analyze()
    assert r["feasible"] is False
    assert r["bottleneck"] == "qubit_count"
    print(f"  PASS  (feasible={r['feasible']}, bottleneck={r['bottleneck']})")


def test_custom_hardware():
    print("\n=== Test: Custom Hardware ===")
    circ = [("H", 0), ("CNOT", 0, 1)]
    custom = {"qubits": 2, "two_qubit_error": 1e-4, "t_gate_error": 1e-4,
              "t_gate_time_ns": 10, "two_qubit_time_ns": 20, "connectivity": "linear"}
    est = ResourceEstimator(circ, hardware=custom)
    r = est.analyze()
    assert r["feasible"] is True
    print(f"  PASS  (custom hw, feasible={r['feasible']})")


def run_all_tests():
    print("=" * 60)
    print("RESOURCE ESTIMATOR TEST SUITE")
    print("=" * 60)
    test_shor_15()
    test_50q_vqe()
    test_1000q_infeasible()
    test_custom_hardware()
    print("\n" + "=" * 60)
    print("ALL RESOURCE ESTIMATOR TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    run_all_tests()
