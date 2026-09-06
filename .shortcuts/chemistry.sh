#!/data/data/com.termux/files/usr/bin/bash
cd ~/quantum/legitimate_quantum_engine_v5.0
python -c "
from legitimate_quantum_engine import ChemistryDriver
driver = ChemistryDriver(molecule='H2', bond_length=0.74)
r = driver.run_uccsd_vqe(max_iter=50, verbose=False)
print('H2 energy:', r['energy'], 'Hartree')
"
read -p "Press Enter..."