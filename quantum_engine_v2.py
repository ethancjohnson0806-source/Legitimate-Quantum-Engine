import numpy as np
import random
import time
import matplotlib.pyplot as plt
from scipy.linalg import expm
from scipy.optimize import minimize

class LegitimateQuantumEngine:
    """
    Refactored Quantum Engine with actual statevector simulation, 
    real XEB, Parallel Tempering, and VQE.
    """
    def __init__(self, num_qubits=6, num_spins=20, seed=42):
        self.n = num_qubits
        self.num_spins = num_spins
        self.dim = 2**self.n
        np.random.seed(seed)
        random.seed(seed)
        
        # Gates
        self.H = 1/np.sqrt(2) * np.array([[1, 1], [1, -1]], dtype=complex)
        self.I = np.eye(2, dtype=complex)
        self.X = np.array([[0, 1], [1, 0]], dtype=complex)
        self.Z = np.array([[1, 0], [0, -1]], dtype=complex)
        
    def rx(self, theta):
        return np.array([[np.cos(theta/2), -1j*np.sin(theta/2)],
                         [-1j*np.sin(theta/2), np.cos(theta/2)]], dtype=complex)

    def rz(self, theta):
        return np.array([[np.exp(-1j*theta/2), 0],
                         [0, np.exp(1j*theta/2)]], dtype=complex)

    def apply_gate(self, state, gate, target):
        """Apply a single-qubit gate using einsum for efficiency."""
        shape = [2] * self.n
        state = state.reshape(shape)
        # The target qubit corresponds to the axis 'target'
        # We want to contract the gate matrix with the state on that axis
        # indices: gate(i, j), state(..., j, ...) -> new_state(..., i, ...)
        indices = list(range(self.n))
        new_indices = list(range(self.n))
        new_indices[target] = self.n # temporary index for the new dimension
        
        # einsum string: 'ij, ...j... -> ...i...'
        # But we need to handle the specific axis. 
        # Easier to use np.tensordot or manual axis swapping.
        state = np.tensordot(gate, state, axes=(1, target))
        # tensordot puts the new axis at the beginning, we need to move it back to 'target'
        state = np.moveaxis(state, 0, target)
        return state.flatten()

    def apply_cz(self, state, q1, q2):
        """Apply CZ gate."""
        shape = [2] * self.n
        state = state.reshape(shape)
        # CZ is diagonal: diag(1, 1, 1, -1)
        # Only state[..., 1, ..., 1, ...] gets multiplied by -1
        slices = [slice(None)] * self.n
        slices[q1] = 1
        slices[q2] = 1
        state[tuple(slices)] *= -1
        return state.flatten()

    # ====================== REAL XEB ======================
    def run_rcs_and_compute_xeb(self, cycles=10):
        state = np.zeros(self.dim, dtype=complex)
        state[0] = 1.0
        
        for _ in range(cycles):
            # Single qubit gates
            for q in range(self.n):
                g_type = random.choice(['H', 'RX', 'RZ'])
                if g_type == 'H':
                    state = self.apply_gate(state, self.H, q)
                elif g_type == 'RX':
                    state = self.apply_gate(state, self.rx(random.uniform(0, 2*np.pi)), q)
                else:
                    state = self.apply_gate(state, self.rz(random.uniform(0, 2*np.pi)), q)
            
            # Entangling gates
            for q in range(self.n - 1):
                if random.random() < 0.9:
                    state = self.apply_cz(state, q, q+1)
        
        probs = np.abs(state)**2
        # Cross-Entropy Benchmarking (XEB)
        # F_XEB = D * <P(x_i)> - 1
        # For exact simulation without noise, this should be close to 1.0 for random circuits
        xeb = self.dim * np.sum(probs**2) - 1
        return xeb

    # ====================== PARALLEL TEMPERING ANNEALING ======================
    def get_energy(self, spins, h, J):
        return -np.sum(h * spins) - np.sum(J * np.outer(spins, spins)) / 2

    def parallel_tempering(self, steps=500, num_replicas=6):
        h = np.random.normal(0, 1.0, self.num_spins)
        J = np.random.normal(0, 1.0, (self.num_spins, self.num_spins))
        J = (J + J.T) / 2
        
        temps = np.geomspace(0.1, 5.0, num_replicas)
        replicas = [np.sign(np.random.randn(self.num_spins)) for _ in range(num_replicas)]
        energies = [self.get_energy(r, h, J) for r in replicas]
        
        best_energy = min(energies)
        
        for step in range(steps):
            for i in range(num_replicas):
                # Metropolis step
                idx = random.randint(0, self.num_spins - 1)
                new_spin = replicas[i].copy()
                new_spin[idx] *= -1
                new_e = self.get_energy(new_spin, h, J)
                
                if new_e < energies[i] or random.random() < np.exp(-(new_e - energies[i]) / temps[i]):
                    replicas[i] = new_spin
                    energies[i] = new_e
                    if new_e < best_energy:
                        best_energy = new_e
            
            # Replica exchange
            if step % 10 == 0:
                for i in range(num_replicas - 1):
                    delta = (1/temps[i] - 1/temps[i+1]) * (energies[i+1] - energies[i])
                    if delta > 0 or random.random() < np.exp(delta):
                        replicas[i], replicas[i+1] = replicas[i+1], replicas[i]
                        energies[i], energies[i+1] = energies[i+1], energies[i]
                        
        return best_energy

    # ====================== VQE WITH EXACT DIAGONALIZATION ======================
    def get_tfim_hamiltonian(self, g=1.0):
        # H = - \sum Z_i Z_{i+1} - g \sum X_i
        H_mat = np.zeros((self.dim, self.dim), dtype=complex)
        
        # Interaction term -Z_i Z_{i+1}
        for i in range(self.n - 1):
            term = 1
            for j in range(self.n):
                if j == i or j == i+1:
                    term = np.kron(term, self.Z)
                else:
                    term = np.kron(term, self.I)
            H_mat -= term
            
        # Transverse field -g X_i
        for i in range(self.n):
            term = 1
            for j in range(self.n):
                if j == i:
                    term = np.kron(term, self.X)
                else:
                    term = np.kron(term, self.I)
            H_mat -= g * term
            
        return H_mat

    def vqe_ansatz(self, params):
        state = np.zeros(self.dim, dtype=complex)
        state[0] = 1.0
        # Simple hardware-efficient ansatz: RY layers + CZ chain
        param_idx = 0
        num_layers = 2
        for _ in range(num_layers):
            for q in range(self.n):
                # RY gate manually
                ry = np.array([[np.cos(params[param_idx]/2), -np.sin(params[param_idx]/2)],
                               [np.sin(params[param_idx]/2), np.cos(params[param_idx]/2)]], dtype=complex)
                state = self.apply_gate(state, ry, q)
                param_idx += 1
            for q in range(self.n - 1):
                state = self.apply_cz(state, q, q+1)
        return state

    def run_vqe(self, H_mat):
        # Exact ground state energy
        evals = np.linalg.eigvalsh(H_mat)
        exact_energy = evals[0]
        
        def objective(params):
            state = self.vqe_ansatz(params)
            energy = np.real(np.conj(state).T @ H_mat @ state)
            return energy
        
        # Use SPSA or simple Nelder-Mead for simulation
        num_params = 2 * self.n # 2 layers
        initial_params = np.random.uniform(0, 2*np.pi, num_params)
        res = minimize(objective, initial_params, method='Nelder-Mead', options={'maxiter': 100})
        
        vqe_energy = res.fun
        error = abs(vqe_energy - exact_energy)
        return error

    # ====================== MAIN EVOLUTION LOOP ======================
    def evolve(self, iterations=30):
        print("🚀 STARTING LEGITIMATE QUANTUM ENGINE EVOLUTION")
        history = []
        H_tfim = self.get_tfim_hamiltonian()
        
        for it in range(iterations):
            xeb = self.run_rcs_and_compute_xeb(cycles=random.randint(5, 15))
            energy = self.parallel_tempering(steps=200)
            vqe_error = self.run_vqe(H_tfim)
            
            # Coherence index: Weighted blend of real metrics
            # Higher XEB (fidelity), Lower Energy (better optimization), Lower VQE error (better accuracy)
            # Normalized/Scaled for visualization
            norm_energy = 1.0 / (1.0 + np.exp(energy/10)) # Sigmoid-like scaling
            coherence = (xeb * 0.4 + norm_energy * 0.4 + (1.0 / (1.0 + vqe_error)) * 0.2)
            
            history.append({
                'iter': it,
                'xeb': xeb,
                'energy': energy,
                'vqe_error': vqe_error,
                'coherence': coherence
            })
            
            if it % 5 == 0:
                print(f"Cycle {it:02d} | XEB: {xeb:.4f} | Energy: {energy:.2f} | VQE Err: {vqe_error:.4f} | Coherence: {coherence:.4f}")
                
        return history

def plot_results(history):
    iters = [h['iter'] for h in history]
    xeb = [h['xeb'] for h in history]
    energy = [h['energy'] for h in history]
    vqe_error = [h['vqe_error'] for h in history]
    coherence = [h['coherence'] for h in history]
    
    fig, axs = plt.subplots(2, 2, figsize=(12, 10))
    fig.suptitle('Quantum Engine Evolution: Legitimate Benchmarking', fontsize=16)
    
    axs[0, 0].plot(iters, xeb, 'b-o', label='XEB Fidelity')
    axs[0, 0].set_title('Cross-Entropy Benchmarking (XEB)')
    axs[0, 0].set_ylabel('Fidelity Proxy')
    axs[0, 0].grid(True)
    
    axs[0, 1].plot(iters, energy, 'r-s', label='Annealing Energy')
    axs[0, 1].set_title('Parallel Tempering Energy')
    axs[0, 1].set_ylabel('Energy (Lower is better)')
    axs[0, 1].grid(True)
    
    axs[1, 0].plot(iters, vqe_error, 'g-^', label='VQE Error')
    axs[1, 0].set_title('VQE Accuracy (TFIM)')
    axs[1, 0].set_ylabel('Energy Error')
    axs[1, 0].grid(True)
    
    axs[1, 1].plot(iters, coherence, 'm-d', label='Coherence Index')
    axs[1, 1].set_title('Unified Coherence Index')
    axs[1, 1].set_ylabel('Coherence')
    axs[1, 1].grid(True)
    
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig('quantum_engine_evolution_v2.png')
    print("Plot saved as quantum_engine_evolution_v2.png")

if __name__ == "__main__":
    engine = LegitimateQuantumEngine(num_qubits=6, num_spins=20)
    history = engine.evolve(iterations=20)
    plot_results(history)
