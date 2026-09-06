#!/data/data/com.termux/files/usr/bin/bash
cd ~/quantum/legitimate_quantum_engine_v5.0
python -c "
from legitimate_quantum_engine import VQE, tfi_hamiltonian
H = tfi_hamiltonian(4)
vqe = VQE(4, H, num_layers=2, max_iterations=200)
r = vqe.solve(verbose=False)
print('Ground state energy:', r['energy'])
"
read -p "Press Enter..."