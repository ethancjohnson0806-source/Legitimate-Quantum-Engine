#!/data/data/com.termux/files/usr/bin/bash
cd ~/quantum/legitimate_quantum_engine_v5.0
python -c "
from legitimate_quantum_engine import StatevectorSim
import numpy as np, random
secret = random.randint(0,15)
n = 4
sim = StatevectorSim(n)
for q in range(n): sim.apply('H', q)
for q in range(n):
    if (secret >> q) & 1: sim.apply('Z', q)
for q in range(n):
    sim.apply('H', q)
    sim.apply('Z', q)
probs = sim.probabilities()
print('Secret was:', secret)
print('Found:', np.argmax(probs))
print('Probability:', round(probs[secret], 3))
"
read -p "Press Enter..."