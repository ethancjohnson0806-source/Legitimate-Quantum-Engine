"""Dynamic circuits: mid-circuit measurement and conditional reset."""
import numpy as np
from .core_simulator import StatevectorSim

class DynamicStatevectorSim(StatevectorSim):
    """Extends StatevectorSim with explicit mid-circuit measurement."""
    def measure(self, qubit):
        probs = self.probabilities()
        p0 = sum(probs[i] for i in range(self.dim) if ((i >> qubit) & 1) == 0)
        outcome = 0 if np.random.random() < p0 else 1
        self.state = np.array([
            self.state[i] if ((i >> qubit) & 1) == outcome else 0
            for i in range(self.dim)
        ], dtype=complex)
        nrm = np.linalg.norm(self.state)
        if nrm > 0:
            self.state /= nrm
        return outcome

    def reset(self, qubit):
        if self.measure(qubit) == 1:
            self.apply("X", qubit)
        return 0

    def conditional_apply(self, control_outcome, target_qubit, gate_name, *gate_args):
        """Classically conditioned gate (for simulation, applies directly
        since the state is already collapsed)."""
        self.apply(gate_name, *gate_args)
