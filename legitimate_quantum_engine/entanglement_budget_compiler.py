"""Entanglement-Budget Compiler — optimizes circuits for MPS friendliness.
Reorders gates and inserts SWAPs to keep bond dimension low.
"""
import numpy as np

class EBCompiler:
    """Compile circuits to minimize MPS bond growth."""

    @staticmethod
    def compile(circuit, budget="mps_chi_32", n_qubits=None):
        """
        Compile a circuit for MPS backend.

        Args:
            circuit: list of (name, *qubits, [theta])
            budget: "mps_chi_X" where X is target bond dimension
            n_qubits: inferred from circuit if None
        """
        if n_qubits is None:
            n_qubits = max(max(g[1:]) for g in circuit if len(g) > 1) + 1

        compiled = []
        for g in circuit:
            name = g[0]
            if name in ("CNOT", "CZ"):
                c, t = g[1], g[2]
                if abs(c - t) == 1:
                    compiled.append(g)
                else:
                    # SWAP chain to bring adjacent
                    path = list(range(min(c, t), max(c, t)))
                    # SWAP qubit t toward c
                    for i in path:
                        compiled.append(("SWAP", i, i + 1))
                    # Apply gate (now adjacent)
                    new_t = t if t > c else c
                    new_c = min(c, t)
                    compiled.append((name, new_c, new_c + 1))
                    # SWAP back
                    for i in reversed(path):
                        compiled.append(("SWAP", i, i + 1))
            else:
                compiled.append(g)
        return compiled

    @staticmethod
    def estimate_bond_growth(circuit, n_qubits):
        """Estimate peak bond dimension for a circuit (toy heuristic)."""
        # Simple heuristic: each long-range gate increases bond
        growth = 1
        for g in circuit:
            if g[0] in ("CNOT", "CZ", "SWAP") and len(g) == 3:
                dist = abs(g[1] - g[2])
                growth = max(growth, 2**dist)
        return min(growth, 2**(n_qubits // 2))
