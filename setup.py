# ===============================================
# Project3_Causal-Uplift-Marketing Setup
# ===============================================
# Business Logic: Makes 'src' an installable package for clean imports.
# This is the industry-standard approach for data science projects.
#
# NOTE: Currently using dynamic sys.path injection in notebooks for quick development.
#       To use this setup file for a more robust solution, run: pip install -e .
#
# Usage:
#   Development mode: pip install -e .
#   Production mode:  pip install .

from setuptools import setup, find_packages

setup(
    name="causal-uplift-marketing",
    version="0.1.0",
    description="Causal inference and uplift modeling for marketing campaigns (Hillstrom dataset)",
    author="CLampard",
    packages=find_packages(),
    python_requires=">=3.9",
    install_requires=[
        # Core data processing
        "pandas>=2.0.0",
        "numpy>=1.24.0",
        
        # Visualization
        "matplotlib>=3.7.0",
        "seaborn>=0.12.0",
        
        # Configuration management
        "pyyaml>=6.0",
        
        # Jupyter support
        "ipython>=8.0.0",
    ],
    extras_require={
        "dev": [
            "jupyter>=1.0.0",
            "notebook>=7.0.0",
        ],
        "ml": [
            # For Phase 2: PSM and Uplift modeling
            "scipy>=1.11.0",
            "scikit-learn>=1.3.0",
            "statsmodels>=0.14.0",
            "xgboost>=2.0.0",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
    ],
)
