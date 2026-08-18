"""Legitimate Quantum Engine v3.0 — Self-Diagnosing Research Platform
Honest core + ADAPT-VQE + MPS + QNG + warm-start + dynamic circuits
+ Schmidt MPS + circuit knitting + entanglement compiler + shadow amputation
+ QITE + adaptive Trotter + duality + orchestrator + shadows + differential sim + stochastic MPS
"""
# Core v2 solvers
from .core_simulator import StatevectorSim
from .vqe_solver import VQE, tfi_hamiltonian, spsa_vqe, vqe_energy, vqe_ansatz
from .qaoa_solver import QAOA, maxcut_hamiltonian
from .quantum_kernel import zz_feature_map, quantum_kernel, kernel_matrix
from .noise_models import apply_pauli_noise, depolarizing_channel
from .qasm_export import export_qasm
from .benchmarks import benchmark_vqe, benchmark_qaoa

# v2.1 upgrades
from .adapt_vqe import ADAPTVQE
from .quantum_natural_gradient import QNGOptimizer
from .qaoa_warm_start import warm_start_angles
from .dynamic_circuits import DynamicStatevectorSim

# v3.0 core modules
from .mps_backend_v2 import MPSStateAdaptive, mps_ghz_state
from .circuit_knitting import knit_expectation
from .entanglement_budget_compiler import EBCompiler
from .shadow_amputation import amputate
from .qite_solver import QITE
from .adaptive_trotter import AdaptiveTrotter
from .circuit_hamiltonian_duality import Duality
from .solver_orchestrator import auto_solve
from .shadow_tomography import ClassicalShadow
from .differential_sim import DifferentialSim
from .stochastic_mps import StochasticMPS

# Optional old-repo modules
try:
    from .sparse_simulator import SparseStateSimulator
except Exception:
    pass
try:
    from .gpu_accelerator import GPUQuantumSimulator
except Exception:
    pass
try:
    from .error_mitigation import ZeroNoiseExtrapolation, ReadoutErrorMitigation
except Exception:
    pass
try:
    from .extended_gates import QuantumGates
except Exception:
    pass

__version__ = "3.0.0-research"
