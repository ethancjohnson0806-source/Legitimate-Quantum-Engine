"""Legitimate Quantum Engine v5.0 -- Impact-First Unified Edition

Pure NumPy core, optional Numba JIT, quantum chemistry, QEC, benchmarks.
Run tests: python -m legitimate_quantum_engine.tests.test_all
"""

# Core simulation backends
from .core.statevector import StatevectorSim
from .core.sparse_hamiltonian import SparseHamiltonian, build_sparse_heisenberg, sparse_lanczos
from .core.stabilizer import StabilizerSim
from .core.noise_models import apply_pauli_noise, depolarizing_channel

# Solvers
from .solvers.vqe_ground import VQE, tfi_hamiltonian, spsa_vqe, vqe_energy, vqe_ansatz
from .solvers.qaoa import QAOA, maxcut_hamiltonian
from .solvers.adapt_vqe import ADAPTVQE
from .solvers.qite import QITE
from .solvers.qng import QNGOptimizer
from .solvers.qaoa_warm_start import warm_start_angles
from .solvers.orchestrator import auto_solve

# Tensor networks
from .tensor_networks.mps_simulator import MPSStateAdaptive, mps_ghz_state
from .tensor_networks.dmrg import DMRG
from .tensor_networks.tdvp import tdvp_evolve
from .tensor_networks.stochastic_mps import StochasticMPS
from .tensor_networks.adaptive_trotter import AdaptiveTrotter

# Quantum chemistry
try:
    from .quantum_chemistry.fermionic_encoding import (
        jordan_wigner_creators, bravyi_kitaev_creators, parity_creators,
        jordan_wigner_annihilators, bravyi_kitaev_annihilators, parity_annihilators,
        multiply_pauli_strings, simplify_pauli_sum
    )
except Exception:
    pass
try:
    from .quantum_chemistry.uccsd_ansatz import UCCSDAnsatz
except Exception:
    pass
try:
    from .quantum_chemistry.chemistry_driver import ChemistryDriver
except Exception:
    pass

# Quantum error correction
from .quantum_error_correction.surface_code import SurfaceCode
from .quantum_error_correction.mwpm_decoder import decode_mwpm, greedy_matching
try:
    from .quantum_error_correction.bp_decoder import BPDecoder
except Exception:
    pass

# Circuit tools
from .circuit_tools.qasm_export import export_qasm
from .circuit_tools.dynamic_circuits import DynamicStatevectorSim
from .circuit_tools.circuit_knitting import knit_expectation
from .circuit_tools.entanglement_budget import EBCompiler
from .circuit_tools.duality import Duality
from .circuit_tools.zx_optimizer import ZXDiagram, simplify
from .circuit_tools.solovay_kitaev import SolovayKitaev

# Characterization
from .characterization.classical_shadows import ClassicalShadow
from .characterization.shadow_tomography import ClassicalShadow as ShadowTomography
from .characterization.shadow_amputation import amputate
from .characterization.differential_sim import DifferentialSim
try:
    from .characterization.quantum_volume import QuantumVolume
except Exception:
    pass
try:
    from .characterization.rb_suite import RandomizedBenchmarking
except Exception:
    pass

# Open systems
from .open_systems.lindblad import (
    build_liouvillian, evolve, steady_state,
    dephasing, amplitude_damping
)

# Monte Carlo
from .monte_carlo.qmc import VMCSolver

# Benchmarks
from .benchmarks.vqe_benchmarks import benchmark_vqe, benchmark_qaoa
from .benchmarks.synthesis_benchmarks import BenchmarkReporter
try:
    from .benchmarks.resource_estimator import ResourceEstimator
except Exception:
    pass

# Utilities
from .utils.symmetry_solver import solve_symmetry_blocked, build_sz_sectors
from .utils.quantum_kernel import zz_feature_map, quantum_kernel, kernel_matrix
from .utils.extended_gates import QuantumGates
from .utils.error_mitigation import ZeroNoiseExtrapolation, ReadoutErrorMitigation
from .utils.gpu_accelerator import GPUQuantumSimulator
try:
    from .utils.jit_backend import JITBackend
except Exception:
    pass

__version__ = "5.0.0-impact-first"
