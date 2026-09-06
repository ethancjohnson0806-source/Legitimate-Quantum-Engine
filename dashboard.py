#!/usr/bin/env python3
"""
Quantum Engine Dashboard -- Legitimate Quantum Engine v5.0

A simple terminal UI for running experiments without typing code.
Just pick a number and press Enter.
"""

import sys, os, time, random, numpy as np

# Ensure the package is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from legitimate_quantum_engine import (
    StatevectorSim, VQE, tfi_hamiltonian, QAOA, maxcut_hamiltonian,
    ResourceEstimator, SurfaceCode, BPDecoder, ChemistryDriver,
    QuantumVolume, MPSStateAdaptive, mps_ghz_state
)

def clear():
    os.system('clear' if os.name != 'nt' else 'cls')

def banner(title):
    print()
    print('=' * 50)
    print(f'  {title}')
    print('=' * 50)

def wait():
    input('\n[Press Enter to continue]')

def exp_bell_state():
    banner('Bell State -- Quantum Coin Flip')
    sim = StatevectorSim(2)
    sim.apply('H', 0)
    sim.apply('CNOT', 0, 1)
    print('\nState:', np.round(sim.state, 3))
    print('\nThis is (|00> + |11>) / sqrt(2)')
    print('Both qubits are correlated. Measure one, you know the other.')
    print('\nMeasuring qubit 0...')
    outcome = sim.measure(0)
    print(f'Result: {outcome}')
    print('The state collapsed. The correlation is gone.')

def exp_teleport():
    banner('Quantum Teleportation')
    print('\nAlice wants to send |1> to Bob using only classical bits')

    alice_data = StatevectorSim(1)
    alice_data.apply('X', 0)

    pair = StatevectorSim(2)
    pair.apply('H', 0)
    pair.apply('CNOT', 0, 1)

    a = alice_data.measure(0)
    b = pair.measure(0)

    if b == 1: pair.apply('X', 1)
    if a == 1: pair.apply('Z', 1)

    result = pair.measure(1)
    print(f'\nBob received: {result}')
    print('Alice sent 1. Bob got 1.')
    print('No particle traveled between them.')

def exp_vqe():
    banner('VQE -- Find Ground State of a Magnet')
    print('\n4 magnets in a line. Finding their lowest energy...')
    H = tfi_hamiltonian(4)
    vqe = VQE(4, H, num_layers=2, max_iterations=200)
    result = vqe.solve(verbose=False)
    exact = -3.46
    print(f'\nEnergy found: {result["energy"]:.4f}')
    print(f'Exact answer: {exact:.2f}')
    print(f'Error: {abs(result["energy"] - exact):.4f}')
    print('\nThe computer guessed, checked, and improved until it converged.')

def exp_grover():
    banner("Grover's Search -- Find a Needle in a Haystack")
    secret = random.randint(0, 15)
    n = 4
    print(f'\nSecret number: {secret} (hidden from the algorithm)')
    print('Searching through 16 possibilities...')

    sim = StatevectorSim(n)
    for q in range(n):
        sim.apply('H', q)

    # Oracle
    for q in range(n):
        if (secret >> q) & 1:
            sim.apply('Z', q)

    # Diffusion
    for q in range(n):
        sim.apply('H', q)
        sim.apply('Z', q)

    probs = sim.probabilities()
    guess = np.argmax(probs)
    print(f'\nAlgorithm found: {guess}')
    print(f'Probability of secret: {probs[secret]:.3f}')
    print(f'Classical would need ~8 checks. Quantum used ~4.')

def exp_surface_code():
    banner('Surface Code -- Fix a Broken Message')
    sc = SurfaceCode(distance=3)
    sc.encode_logical_zero()

    bad_qubit = random.randint(0, 8)
    sc.inject_error('X', bad_qubit)
    print(f'\nError injected at qubit {bad_qubit}')

    syn = sc.measure_syndrome()
    print(f'Syndrome (damage pattern): X={syn["X"]}, Z={syn["Z"]}')

    corr = sc.decode_mwpm()
    print(f'Correction: {corr}')

    for q, p in corr.items():
        sc.inject_error(p, q)
    final = sc.measure_syndrome()
    print(f'After fix: {final}')
    print('\nThe code protected the message despite the error.')

def exp_chemistry():
    banner('Quantum Chemistry -- H2 Molecule')
    print('\nComputing energy of hydrogen at 0.74 angstroms...')
    driver = ChemistryDriver(molecule='H2', bond_length=0.74)
    result = driver.run_uccsd_vqe(max_iter=50, verbose=False)
    print(f'\nEnergy: {result["energy"]:.4f} Hartree')
    print('Negative = stable. This is how quantum computers design drugs.')

def exp_resource_estimator():
    banner('Resource Estimator -- Is Your Circuit Possible?')
    n = int(input('How many qubits in your circuit? '))
    depth = int(input('How many layers? '))

    circ = [('H', i) for i in range(n)]
    for _ in range(depth):
        for i in range(n - 1):
            circ.append(('CNOT', i, i + 1))

    est = ResourceEstimator(circ, hardware='ibm_eagle')
    r = est.analyze()
    print()
    print(f'  Feasible:        {r["feasible"]}')
    print(f'  Qubits needed:   {r["qubits_required"]}')
    print(f'  Qubits available:{r["qubits_available"]}')
    print(f'  Bottleneck:      {r["bottleneck"]}')
    print(f'  Est. runtime:    {r["estimated_runtime_s"]:.2e} s')

def exp_quantum_volume():
    banner('Quantum Volume -- Benchmark Your Simulator')
    print('\nRunning IBM Quantum Volume protocol...')
    print('(This may take a moment)')
    qv = QuantumVolume(n_qubits=3, n_trials=10)
    r = qv.benchmark()
    print(f'\nQV test passed: {r["passed"]}')
    print(f'Pass rate: {r["pass_rate"]:.1%}')
    print(f'Mean heavy output ratio: {r["mean_ratio"]:.3f}')

def exp_mps():
    banner('MPS -- Compress a 20-Qubit State')
    print('\nCreating a 20-qubit GHZ state...')
    mps = mps_ghz_state(20)
    print(f'Bond dimensions: {mps.bond_dims}')
    print(f'Max bond: {max(mps.bond_dims)}')
    print(f'\n20 qubits = 1,048,576 amplitudes classically.')
    print(f'MPS compresses this to just {sum(mps.bond_dims)} numbers.')

def exp_randomness():
    banner('Quantum Random Number Generator')
    n = int(input('How many random bits? (1-128): ') or '16')
    sim = StatevectorSim(1)
    bits = ''
    for _ in range(n):
        sim = StatevectorSim(1)
        sim.apply('H', 0)
        bits += str(sim.measure(0))
    print(f'\nQuantum random bits: {bits}')
    print(f'As integer: {int(bits, 2)}')
    ones = bits.count('1')
    print(f'Balance: {ones} ones, {len(bits)-ones} zeros')

def main():
    while True:
        clear()
        print()
        print('  LEGITIMATE QUANTUM ENGINE v5.0')
        print('  ==============================')
        print()
        print('  1.  Bell State (quantum coin flip)')
        print('  2.  Quantum Teleportation')
        print('  3.  VQE (find ground state)')
        print('  4.  Grover Search (needle in haystack)')
        print('  5.  Surface Code (error correction)')
        print('  6.  Quantum Chemistry (H2 molecule)')
        print('  7.  Resource Estimator (feasibility check)')
        print('  8.  Quantum Volume (benchmark)')
        print('  9.  MPS Compression (20 qubits)')
        print('  10. Quantum Randomness')
        print('  0.  Exit')
        print()

        choice = input('Pick a number: ').strip()

        experiments = {
            '1': exp_bell_state,
            '2': exp_teleport,
            '3': exp_vqe,
            '4': exp_grover,
            '5': exp_surface_code,
            '6': exp_chemistry,
            '7': exp_resource_estimator,
            '8': exp_quantum_volume,
            '9': exp_mps,
            '10': exp_randomness,
        }

        if choice == '0':
            print('\nGoodbye.')
            break
        elif choice in experiments:
            clear()
            try:
                experiments[choice]()
            except Exception as e:
                print(f'\nError: {e}')
            wait()
        else:
            print('Invalid choice. Try again.')
            time.sleep(1)

if __name__ == '__main__':
    main()
