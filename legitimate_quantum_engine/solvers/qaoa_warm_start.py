"""QAOA warm-start from classical greedy MaxCut solution."""
import numpy as np

def greedy_maxcut_cut(n_nodes, edges):
    """Fast greedy classical MaxCut approximation."""
    cut = [0] * n_nodes
    for _ in range(3):  # a few sweeps
        for node in range(n_nodes):
            gain = 0
            for (i, j) in edges:
                if i == node:
                    gain += 1 if cut[j] == cut[node] else -1
                elif j == node:
                    gain += 1 if cut[i] == cut[node] else -1
            if gain > 0:
                cut[node] = 1 - cut[node]
    return cut

def warm_start_angles(n_nodes, edges, p=1):
    """Initialize QAOA angles from greedy classical solution."""
    cut = greedy_maxcut_cut(n_nodes, edges)
    cut_val = sum(1 for (i, j) in edges if cut[i] != cut[j])
    frac = cut_val / len(edges) if edges else 0.5
    gamma = 0.2 + 0.3 * frac
    beta = 0.1 + 0.1 * frac
    params = []
    for _ in range(p):
        params.extend([gamma, beta])
    return np.array(params)
