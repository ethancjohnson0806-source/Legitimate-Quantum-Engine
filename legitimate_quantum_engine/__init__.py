"""Legitimate Quantum Engine - A unified, physics-grounded quantum simulation platform

Version: 5.1.0
Author: Ethan C. Johnson
License: MIT
"""

__version__ = "5.1.0"
__author__ = "Ethan C. Johnson"
__license__ = "MIT"

# Import core components
try:
    from .quantum_engine_v5_unified import QuantumEngine, QuantumCircuit
except ImportError:
    pass

try:
    from .quantum_ibm_integration import IBMQuantumBridge, HybridExecutor
except ImportError:
    pass

try:
    from .quantum_distributed_computing import DistributedQuantumExecutor
except ImportError:
    pass

try:
    from .quantum_advanced_algorithms import VariationalQuantumDeflation, ADAPTVariationalQuantumEigensolver, EnhancedQAOA
except ImportError:
    pass

try:
    from .quantum_advanced_noise_models import RealisticQuantumSimulator, NoiseModelLibrary
except ImportError:
    pass

try:
    from .quantum_novel_optimization_techniques import BarrenPlateauMitigation, QuantumNeuralNetworkOptimizer
except ImportError:
    pass

__all__ = [
    "QuantumEngine",
    "QuantumCircuit",
    "IBMQuantumBridge",
    "HybridExecutor",
    "DistributedQuantumExecutor",
    "VariationalQuantumDeflation",
    "ADAPTVariationalQuantumEigensolver",
    "EnhancedQAOA",
    "RealisticQuantumSimulator",
    "NoiseModelLibrary",
    "BarrenPlateauMitigation",
    "QuantumNeuralNetworkOptimizer",
]
