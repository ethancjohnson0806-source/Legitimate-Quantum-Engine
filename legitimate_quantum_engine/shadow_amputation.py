"""Shadow-Based Circuit Amputation — delete gates that don't affect observables.
Uses classical shadows to empirically test gate relevance.
"""
import numpy as np
from .core_simulator import StatevectorSim
from .classical_shadows import ClassicalShadow

def amputate(circuit, observable, n_qubits, shadow_shots=500, tolerance=0.01, verbose=False):
    """
    Iteratively remove gates whose deletion doesn't change <observable> beyond tolerance.

    Args:
        circuit: list of (name, *args)
        observable: Hermitian matrix
        n_qubits: number of qubits
        shadow_shots: number of shadow measurements
        tolerance: max allowed change in expectation

    Returns:
        pruned circuit
    """
    # For small n, use exact statevector instead of shadows (more reliable)
    if n_qubits <= 10:
        return _exact_amputate(circuit, observable, n_qubits, tolerance, verbose)

    # Shadow-based for larger n
    pruned = circuit[:]
    changed = True
    iteration = 0
    while changed and iteration < 3:
        changed = False
        iteration += 1
        # Take shadow of current pruned circuit
        shadow = ClassicalShadow(n_qubits, num_snapshots=shadow_shots)
        sim = StatevectorSim(n_qubits)
        for g in pruned:
            sim.apply(*g)
        shadow.capture(sim)

        baseline = shadow.expectation(observable)

        i = 0
        while i < len(pruned):
            test = pruned[:i] + pruned[i+1:]
            sim = StatevectorSim(n_qubits)
            for g in test:
                sim.apply(*g)
            shadow_test = ClassicalShadow(n_qubits, num_snapshots=min(200, shadow_shots))
            shadow_test.capture(sim)
            test_exp = shadow_test.expectation(observable)

            if abs(test_exp - baseline) < tolerance:
                pruned.pop(i)
                changed = True
                if verbose:
                    print(f"  Removed gate {i}: |{test_exp - baseline:.4f}| < {tolerance}")
            else:
                i += 1
    return pruned

def _exact_amputate(circuit, observable, n_qubits, tolerance, verbose):
    """Exact version for small circuits."""
    pruned = circuit[:]
    changed = True
    while changed:
        changed = False
        # Baseline
        sim = StatevectorSim(n_qubits)
        for g in pruned:
            sim.apply(*g)
        baseline = float(np.real(np.vdot(sim.state, observable @ sim.state)))

        i = 0
        while i < len(pruned):
            test = pruned[:i] + pruned[i+1:]
            sim = StatevectorSim(n_qubits)
            for g in test:
                sim.apply(*g)
            val = float(np.real(np.vdot(sim.state, observable @ sim.state)))
            if abs(val - baseline) < tolerance:
                if verbose:
                    print(f"  Removed gate {i}: |{val - baseline:.6f}| < {tolerance}")
                pruned.pop(i)
                changed = True
            else:
                i += 1
    return pruned
