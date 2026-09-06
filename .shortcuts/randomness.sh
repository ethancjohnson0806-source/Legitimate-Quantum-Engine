#!/data/data/com.termux/files/usr/bin/bash
cd ~/quantum/legitimate_quantum_engine_v5.0
python -c "
from legitimate_quantum_engine import StatevectorSim
bits = ''
for _ in range(32):
    s = StatevectorSim(1)
    s.apply('H', 0)
    bits += str(s.measure(0))
print('32 quantum random bits:')
print(bits)
print('As integer:', int(bits, 2))
"
read -p "Press Enter..."