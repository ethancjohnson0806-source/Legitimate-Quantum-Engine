"""
Distributed Computing Framework for Quantum Engine
Enables parallel execution across multiple nodes
Supports parameter sweeps, ensemble averaging, and distributed optimization
"""

import json
import time
import hashlib
from typing import Dict, List, Tuple, Optional, Callable, Any
from dataclasses import dataclass, asdict
from enum import Enum
import numpy as np
from collections import defaultdict


class DistributionStrategy(Enum):
    """Strategies for distributing quantum jobs"""
    PARAMETER_SWEEP = "parameter_sweep"
    ENSEMBLE_AVERAGING = "ensemble_averaging"
    CIRCUIT_PARTITIONING = "circuit_partitioning"
    OPTIMIZATION_PARALLEL = "optimization_parallel"


@dataclass
class DistributedJob:
    """Represents a distributed quantum job"""
    job_id: str
    strategy: DistributionStrategy
    total_tasks: int
    completed_tasks: int = 0
    failed_tasks: int = 0
    results: List[Dict[str, Any]] = None
    start_time: float = 0.0
    end_time: Optional[float] = None
    status: str = "pending"

    def __post_init__(self):
        if self.results is None:
            self.results = []


@dataclass
class ComputeNode:
    """Represents a compute node in the distributed system"""
    node_id: str
    capacity: int  # Number of concurrent jobs
    current_load: int = 0
    total_jobs_processed: int = 0
    total_execution_time: float = 0.0
    is_available: bool = True


class DistributedQuantumExecutor:
    """Manages distributed execution of quantum jobs"""

    def __init__(self, num_nodes: int = 4):
        self.nodes = [
            ComputeNode(node_id=f"node_{i}", capacity=4)
            for i in range(num_nodes)
        ]
        self.job_queue = []
        self.active_jobs = {}
        self.completed_jobs = {}
        self.job_results_cache = {}

    def submit_parameter_sweep(
        self,
        base_circuit: Dict[str, Any],
        parameter_ranges: Dict[str, List[float]],
        circuit_builder: Callable
    ) -> str:
        """Submit parameter sweep job"""

        # Generate all parameter combinations
        param_names = list(parameter_ranges.keys())
        param_values = list(parameter_ranges.values())

        total_combinations = 1
        for values in param_values:
            total_combinations *= len(values)

        job_id = self._generate_job_id("param_sweep")
        job = DistributedJob(
            job_id=job_id,
            strategy=DistributionStrategy.PARAMETER_SWEEP,
            total_tasks=total_combinations
        )

        # Create tasks for each parameter combination
        tasks = []
        for combo_idx in range(total_combinations):
            params = {}
            temp_idx = combo_idx

            for i, param_name in enumerate(param_names):
                param_idx = temp_idx % len(param_values[i])
                params[param_name] = param_values[i][param_idx]
                temp_idx //= len(param_values[i])

            circuit = circuit_builder(base_circuit, params)
            tasks.append({
                "task_id": f"{job_id}_task_{combo_idx}",
                "circuit": circuit,
                "parameters": params,
                "status": "pending"
            })

        job.results = tasks
        self.active_jobs[job_id] = job
        self._distribute_tasks(job_id, tasks)

        print(f"✓ Parameter sweep submitted: {job_id} ({total_combinations} tasks)")
        return job_id

    def submit_ensemble_averaging(
        self,
        circuit: Dict[str, Any],
        num_runs: int = 100,
        shots_per_run: int = 1024
    ) -> str:
        """Submit ensemble averaging job"""

        job_id = self._generate_job_id("ensemble")
        job = DistributedJob(
            job_id=job_id,
            strategy=DistributionStrategy.ENSEMBLE_AVERAGING,
            total_tasks=num_runs
        )

        # Create tasks for each ensemble run
        tasks = []
        for run_idx in range(num_runs):
            tasks.append({
                "task_id": f"{job_id}_run_{run_idx}",
                "circuit": circuit,
                "shots": shots_per_run,
                "run_index": run_idx,
                "status": "pending"
            })

        job.results = tasks
        self.active_jobs[job_id] = job
        self._distribute_tasks(job_id, tasks)

        print(f"✓ Ensemble averaging submitted: {job_id} ({num_runs} runs)")
        return job_id

    def submit_circuit_partitioning(
        self,
        circuit: Dict[str, Any],
        partition_strategy: str = "balanced"
    ) -> str:
        """Submit circuit partitioning job"""

        job_id = self._generate_job_id("partition")

        # Partition circuit into independent subcircuits
        partitions = self._partition_circuit(circuit, partition_strategy)

        job = DistributedJob(
            job_id=job_id,
            strategy=DistributionStrategy.CIRCUIT_PARTITIONING,
            total_tasks=len(partitions)
        )

        tasks = []
        for part_idx, partition in enumerate(partitions):
            tasks.append({
                "task_id": f"{job_id}_partition_{part_idx}",
                "circuit": partition,
                "partition_index": part_idx,
                "status": "pending"
            })

        job.results = tasks
        self.active_jobs[job_id] = job
        self._distribute_tasks(job_id, tasks)

        print(f"✓ Circuit partitioning submitted: {job_id} ({len(partitions)} partitions)")
        return job_id

    def submit_parallel_optimization(
        self,
        circuit_template: Dict[str, Any],
        optimizer_configs: List[Dict[str, Any]]
    ) -> str:
        """Submit parallel optimization with different optimizers"""

        job_id = self._generate_job_id("opt_parallel")
        job = DistributedJob(
            job_id=job_id,
            strategy=DistributionStrategy.OPTIMIZATION_PARALLEL,
            total_tasks=len(optimizer_configs)
        )

        tasks = []
        for opt_idx, config in enumerate(optimizer_configs):
            tasks.append({
                "task_id": f"{job_id}_optimizer_{opt_idx}",
                "circuit": circuit_template,
                "optimizer_config": config,
                "optimizer_index": opt_idx,
                "status": "pending"
            })

        job.results = tasks
        self.active_jobs[job_id] = job
        self._distribute_tasks(job_id, tasks)

        print(f"✓ Parallel optimization submitted: {job_id} ({len(optimizer_configs)} optimizers)")
        return job_id

    def _distribute_tasks(self, job_id: str, tasks: List[Dict[str, Any]]):
        """Distribute tasks across available nodes"""

        task_idx = 0
        for task in tasks:
            # Find least loaded node
            best_node = min(self.nodes, key=lambda n: n.current_load if n.is_available else float('inf'))

            if best_node.current_load < best_node.capacity:
                best_node.current_load += 1
                task["assigned_node"] = best_node.node_id
                task["status"] = "assigned"
            else:
                task["status"] = "queued"

            task_idx += 1

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of a distributed job"""

        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            return {
                "job_id": job_id,
                "status": job.status,
                "strategy": job.strategy.value,
                "total_tasks": job.total_tasks,
                "completed_tasks": job.completed_tasks,
                "failed_tasks": job.failed_tasks,
                "progress": (job.completed_tasks / job.total_tasks * 100) if job.total_tasks > 0 else 0,
                "elapsed_time": time.time() - job.start_time if job.start_time else 0
            }

        elif job_id in self.completed_jobs:
            job = self.completed_jobs[job_id]
            return {
                "job_id": job_id,
                "status": "completed",
                "strategy": job.strategy.value,
                "total_tasks": job.total_tasks,
                "completed_tasks": job.completed_tasks,
                "failed_tasks": job.failed_tasks,
                "total_time": job.end_time - job.start_time if job.end_time else 0
            }

        return {"status": "not_found", "job_id": job_id}

    def get_aggregated_results(self, job_id: str) -> Dict[str, Any]:
        """Get aggregated results from a completed job"""

        if job_id not in self.job_results_cache:
            return {"status": "not_ready", "job_id": job_id}

        results = self.job_results_cache[job_id]

        if job_id in self.active_jobs:
            job = self.active_jobs[job_id]
            strategy = job.strategy
        else:
            job = self.completed_jobs.get(job_id)
            strategy = job.strategy if job else None

        aggregation = {
            "job_id": job_id,
            "strategy": strategy.value if strategy else None,
            "num_results": len(results),
            "raw_results": results
        }

        # Strategy-specific aggregation
        if strategy == DistributionStrategy.ENSEMBLE_AVERAGING:
            aggregation["ensemble_mean"] = np.mean([r.get("value", 0) for r in results])
            aggregation["ensemble_std"] = np.std([r.get("value", 0) for r in results])

        elif strategy == DistributionStrategy.PARAMETER_SWEEP:
            aggregation["best_result"] = max(results, key=lambda r: r.get("fidelity", 0), default=None)
            aggregation["worst_result"] = min(results, key=lambda r: r.get("fidelity", 0), default=None)

        elif strategy == DistributionStrategy.OPTIMIZATION_PARALLEL:
            aggregation["best_optimizer"] = max(results, key=lambda r: r.get("convergence", 0), default=None)

        return aggregation

    def simulate_execution(self, job_id: str, execution_time_per_task: float = 0.1):
        """Simulate job execution"""

        if job_id not in self.active_jobs:
            return {"status": "job_not_found"}

        job = self.active_jobs[job_id]
        job.status = "running"
        job.start_time = time.time()

        # Simulate task execution
        results = []
        for task_idx in range(job.total_tasks):
            # Simulate execution
            exec_time = execution_time_per_task + np.random.normal(0, 0.01)
            result = {
                "task_id": f"{job_id}_task_{task_idx}",
                "execution_time": max(0.01, exec_time),
                "fidelity": np.random.uniform(0.65, 0.85),
                "convergence": np.random.uniform(0.7, 0.99),
                "value": np.random.uniform(-100, 100)
            }
            results.append(result)
            job.completed_tasks += 1

        job.status = "completed"
        job.end_time = time.time()
        self.job_results_cache[job_id] = results

        # Move to completed jobs
        self.completed_jobs[job_id] = job
        del self.active_jobs[job_id]

        return {
            "job_id": job_id,
            "status": "completed",
            "total_time": job.end_time - job.start_time,
            "results_count": len(results)
        }

    def get_cluster_stats(self) -> Dict[str, Any]:
        """Get statistics about the compute cluster"""

        total_capacity = sum(node.capacity for node in self.nodes)
        total_load = sum(node.current_load for node in self.nodes)
        total_jobs_processed = sum(node.total_jobs_processed for node in self.nodes)

        return {
            "num_nodes": len(self.nodes),
            "total_capacity": total_capacity,
            "current_load": total_load,
            "utilization": (total_load / total_capacity * 100) if total_capacity > 0 else 0,
            "total_jobs_processed": total_jobs_processed,
            "active_jobs": len(self.active_jobs),
            "completed_jobs": len(self.completed_jobs),
            "nodes": [
                {
                    "node_id": node.node_id,
                    "capacity": node.capacity,
                    "current_load": node.current_load,
                    "utilization": (node.current_load / node.capacity * 100) if node.capacity > 0 else 0,
                    "jobs_processed": node.total_jobs_processed
                }
                for node in self.nodes
            ]
        }

    def _partition_circuit(self, circuit: Dict[str, Any], strategy: str) -> List[Dict[str, Any]]:
        """Partition circuit into independent subcircuits"""

        gates = circuit.get("gates", [])

        if strategy == "balanced":
            # Split gates evenly
            num_partitions = min(4, max(1, len(gates) // 5))
            partition_size = len(gates) // num_partitions

            partitions = []
            for p in range(num_partitions):
                start = p * partition_size
                end = start + partition_size if p < num_partitions - 1 else len(gates)

                partition = {
                    "num_qubits": circuit.get("num_qubits", 2),
                    "gates": gates[start:end],
                    "partition_id": p
                }
                partitions.append(partition)

            return partitions

        else:
            # Default: return single partition
            return [circuit]

    def _generate_job_id(self, prefix: str) -> str:
        """Generate unique job ID"""
        timestamp = str(time.time()).encode()
        hash_suffix = hashlib.md5(timestamp).hexdigest()[:8]
        return f"{prefix}_{hash_suffix}"


def test_distributed_computing():
    """Test distributed computing framework"""

    print("\n" + "="*60)
    print("DISTRIBUTED COMPUTING FRAMEWORK TEST")
    print("="*60)

    executor = DistributedQuantumExecutor(num_nodes=4)

    # Test 1: Parameter sweep
    print("\n1. Testing parameter sweep...")
    base_circuit = {
        "num_qubits": 2,
        "gates": [{"name": "h", "qubits": [0], "params": []}]
    }

    def circuit_builder(base, params):
        circuit = base.copy()
        circuit["gates"].append({
            "name": "ry",
            "qubits": [0],
            "params": [params.get("theta", 0)]
        })
        return circuit

    param_ranges = {"theta": [0, np.pi/4, np.pi/2, 3*np.pi/4, np.pi]}
    job_id = executor.submit_parameter_sweep(base_circuit, param_ranges, circuit_builder)
    executor.simulate_execution(job_id, execution_time_per_task=0.05)
    status = executor.get_job_status(job_id)
    print(f"   ✓ Parameter sweep completed: {status['completed_tasks']} tasks")

    # Test 2: Ensemble averaging
    print("\n2. Testing ensemble averaging...")
    job_id = executor.submit_ensemble_averaging(base_circuit, num_runs=50)
    executor.simulate_execution(job_id, execution_time_per_task=0.02)
    status = executor.get_job_status(job_id)
    print(f"   ✓ Ensemble averaging completed: {status['completed_tasks']} runs")

    # Test 3: Cluster statistics
    print("\n3. Testing cluster statistics...")
    stats = executor.get_cluster_stats()
    print(f"   ✓ Cluster utilization: {stats['utilization']:.1f}%")
    print(f"   ✓ Total jobs processed: {stats['total_jobs_processed']}")

    print("\n" + "="*60)
    print("DISTRIBUTED COMPUTING TEST COMPLETE")
    print("="*60 + "\n")

    return {
        "parameter_sweep_results": executor.get_aggregated_results(job_id),
        "cluster_stats": stats
    }


if __name__ == "__main__":
    test_distributed_computing()
