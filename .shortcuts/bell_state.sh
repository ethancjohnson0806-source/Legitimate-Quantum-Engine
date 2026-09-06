#!/data/data/com.termux/files/usr/bin/bash
cd ~/quantum/legitimate_quantum_engine_v5.0
python -c "
from legitimate_quantum_engine import StatevectorSim
import numpy as np
sim = StatevectorSim(2)
sim.apply('H', 0)
sim.apply('CNOT', 0, 1)
print('Bell state:', np.round(sim.state, 3))
print('Measure qubit 0:', sim.measure(0))
"
read -p "Press Enter..."