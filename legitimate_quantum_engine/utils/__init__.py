"""Legitimate Quantum Engine -- Utilities."""
from .symmetry_solver import solve_symmetry_blocked, build_sz_sectors
from .quantum_kernel import zz_feature_map, quantum_kernel, kernel_matrix
from .extended_gates import QuantumGates
from .error_mitigation import ZeroNoiseExtrapolation, ReadoutErrorMitigation
try:
    from .gpu_accelerator import GPUQuantumSimulator
except Exception:
    pass
try:
    from .jit_backend import JITBackend
except ImportError:
    pass
