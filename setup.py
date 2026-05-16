#!/usr/bin/env python3
"""
Setup configuration for Legitimate Quantum Engine
Enables installation via: pip install legitimate-quantum-engine
"""

from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="legitimate-quantum-engine",
    version="5.1.0",
    author="Ethan C. Johnson",
    author_email="ethancjohnson0806@gmail.com",
    description="A unified, physics-grounded quantum simulation engine with 15+ optimization techniques, IBM Quantum integration, and realistic noise modeling",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ethancjohnson0806-source/Legitimate-Quantum-Engine",
    project_urls={
        "Bug Tracker": "https://github.com/ethancjohnson0806-source/Legitimate-Quantum-Engine/issues",
        "Documentation": "https://github.com/ethancjohnson0806-source/Legitimate-Quantum-Engine/blob/main/QUANTUM_ENGINE_MEGA_COCKTAIL_DOCS.md",
        "Source Code": "https://github.com/ethancjohnson0806-source/Legitimate-Quantum-Engine",
    },
    packages=["legitimate_quantum_engine"],
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Science/Research",
        "Intended Audience :: Developers",
        "Topic :: Scientific/Engineering :: Physics",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=[
        "numpy>=1.20.0",
        "scipy>=1.7.0",
        "matplotlib>=3.4.0",
    ],
    extras_require={
        "dev": [
            "pytest>=6.0",
            "pytest-cov>=2.12.0",
            "black>=21.0",
            "flake8>=3.9.0",
            "mypy>=0.910",
        ],
        "gpu": [
            "cupy>=9.0.0",
        ],
        "ibm": [
            "qiskit>=0.36.0",
            "qiskit-ibm-runtime>=0.8.0",
        ],
        "ml": [
            "scikit-learn>=0.24.0",
            "pennylane>=0.28.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "quantum-engine=quantum_engine_v5_unified:main",
        ],
    },
    keywords="quantum computing simulation VQE QAOA optimization algorithms",
    zip_safe=False,
)
