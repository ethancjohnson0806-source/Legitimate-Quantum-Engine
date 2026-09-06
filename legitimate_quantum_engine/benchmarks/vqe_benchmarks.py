import time
import numpy as np
from ..solvers.vqe_ground import tfi_hamiltonian, spsa_vqe
from ..solvers.qaoa import maxcut_hamiltonian, spsa_qaoa

def benchmark_vqe(n_list=[4, 6], layers=2, iterations=300):
    print("VQE Benchmark")
    for n in n_list:
        H = tfi_hamiltonian(n, J=1.0, h=0.5)
        t0 = time.time()
        e, theta, hist = spsa_vqe(H, n, layers, max_iter=iterations, verbose=False)
        elapsed = time.time() - t0
        exact = np.min(np.linalg.eigvalsh(H))
        err = abs(e - exact) / abs(exact) if exact != 0 else abs(e)
        status = "PASS" if err < 0.15 else "NEEDS_MORE_ITERATIONS"
        print(f"n={n:2d} | energy={e:.6f} | exact={exact:.6f} | error={err:.4f} | time={elapsed:.3f}s | {status}")

def benchmark_qaoa(n_list=[3, 4], p=1, trials=300):
    print("QAOA Benchmark (MaxCut on cycle graph)")
    for n in n_list:
        edges = [(i, (i + 1) % n) for i in range(n)]
        H = maxcut_hamiltonian(n, edges)
        exact = np.min(np.linalg.eigvalsh(H))
        t0 = time.time()
        e, theta, hist = spsa_qaoa(H, n, edges, p, max_iter=trials, verbose=False)
        elapsed = time.time() - t0
        err = abs(e - exact) / abs(exact) if exact != 0 else abs(e)
        status = "PASS" if err < 0.15 else "NEEDS_MORE_ITERATIONS"
        print(f"n={n:2d} | energy={e:.6f} | exact={exact:.6f} | error={err:.4f} | time={elapsed:.3f}s | {status}")
