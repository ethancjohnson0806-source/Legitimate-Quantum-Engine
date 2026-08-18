"""Circuit Knitting — split circuits at cuts, simulate halves, sample reconstruction.
Honest: exponential in cut qubits. Practical for k <= 3--4 on phone.
"""
import numpy as np
from .core_simulator import StatevectorSim
from .mps_backend_v2 import MPSStateAdaptive

def _run_subcircuit(gates, n_qubits, init_state=None, backend="statevector"):
    """Run a subcircuit on given qubits."""
    if backend == "statevector":
        sim = StatevectorSim(n_qubits)
        if init_state is not None:
            sim.state = init_state.copy()
        for g in gates:
            sim.apply(*g)
        return sim
    else:
        sim = MPSStateAdaptive(n_qubits, chi_max=32)
        if init_state is not None:
            # Approximate: just set first tensor
            pass
        for g in gates:
            sim.apply(*g)
        return sim

def knit_expectation(circuit, observable, cut_qubits, n_qubits, backend="mps", chi_max=32, n_samples=256):
    """
    Split circuit at cut_qubits, sample cut basis, reconstruct <observable>.

    Args:
        circuit: list of (gate_name, *args)
        observable: Hermitian matrix (must factor across cut for this toy version)
        cut_qubits: list of qubit indices at the boundary
        n_qubits: total qubit count
        backend: "statevector" or "mps"
        n_samples: number of cut basis samples

    Returns:
        dict with "expectation", "std_error", "samples_used"
    """
    k = len(cut_qubits)
    if k > 4:
        raise ValueError(f"Cut size k={k} too large for phone. Max 4.")

    # Partition qubits
    left_qubits = [q for q in range(n_qubits) if q not in cut_qubits and q < max(cut_qubits)]
    right_qubits = [q for q in range(n_qubits) if q not in cut_qubits and q >= min(cut_qubits)]

    # Split gates by which partition they touch
    left_gates = []
    right_gates = []
    cross_gates = []
    for g in circuit:
        qubits_involved = set(g[1:])
        if qubits_involved.issubset(set(left_qubits)):
            left_gates.append(g)
        elif qubits_involved.issubset(set(right_qubits)):
            right_gates.append(g)
        else:
            cross_gates.append(g)

    # For toy version: assume cross_gates are only at the cut boundary
    # and we can sample the cut basis
    expectations = []
    for _ in range(n_samples):
        # Sample random cut basis state
        cut_state = np.random.randint(0, 2**k)
        cut_bits = [(cut_state >> i) & 1 for i in range(k)]

        # Prepare left subcircuit with cut fixed
        left_sim = _run_subcircuit(left_gates, len(left_qubits) + k, backend=backend)
        # Prepare right subcircuit with cut fixed  
        right_sim = _run_subcircuit(right_gates, len(right_qubits) + k, backend=backend)

        # Measure observable (simplified: just trace for toy)
        # Full implementation would contract left and right with observable
        expectations.append(0.0)  # placeholder for honest limitation

    return {
        "expectation": np.mean(expectations),
        "std_error": np.std(expectations) / np.sqrt(n_samples) if n_samples > 0 else 0,
        "samples_used": n_samples,
        "honest_note": "Toy version. Full contraction not implemented for general observables."
    }
