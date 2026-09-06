#!/data/data/com.termux/files/usr/bin/bash
cd ~/quantum/legitimate_quantum_engine_v5.0
python -c "
from legitimate_quantum_engine import SurfaceCode
import random
sc = SurfaceCode(distance=3)
sc.encode_logical_zero()
q = random.randint(0,8)
sc.inject_error('X', q)
print('Error at qubit:', q)
syn = sc.measure_syndrome()
print('Syndrome:', syn)
corr = sc.decode_mwpm()
print('Correction:', corr)
"
read -p "Press Enter..."