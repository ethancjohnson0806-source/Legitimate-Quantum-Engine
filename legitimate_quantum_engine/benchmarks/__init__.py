"""Legitimate Quantum Engine -- Benchmarks and resource estimation."""
from .vqe_benchmarks import benchmark_vqe, benchmark_qaoa
from .synthesis_benchmarks import BenchmarkReporter
try:
    from .resource_estimator import ResourceEstimator
except ImportError:
    pass
