import numpy as np
from .core_simulator import StatevectorSim

def zz_feature_map(x, n_qubits, reps=2):
    """ZZ feature map for quantum kernel."""
    sim = StatevectorSim(n_qubits)
    for r in range(reps):
        for i, val in enumerate(x[:n_qubits]):
            sim.apply("RZ", 2 * val, i)
        for i in range(n_qubits - 1):
            sim.apply("CNOT", i, i + 1)
            sim.apply("RZ", 2 * (np.pi - x[i]) * (np.pi - x[i + 1]), i + 1)
            sim.apply("CNOT", i, i + 1)
    return sim

def quantum_kernel(x1, x2, n_qubits=4, reps=2):
    """Quantum kernel fidelity |<phi(x1)|phi(x2)>|^2."""
    sim1 = zz_feature_map(x1, n_qubits, reps)
    sim2 = zz_feature_map(x2, n_qubits, reps)
    fidelity = abs(np.vdot(sim1.state, sim2.state)) ** 2
    return fidelity

def kernel_matrix(X, n_qubits=4, reps=2):
    """Compute kernel matrix for dataset X."""
    n = len(X)
    K = np.zeros((n, n))
    for i in range(n):
        for j in range(i, n):
            k = quantum_kernel(X[i], X[j], n_qubits, reps)
            K[i, j] = k
            K[j, i] = k
    return K
