"""Probability-aware short-block ECC synthesis and verification.

The package is deliberately separate from :mod:`architecture`: codeforge
creates and certifies candidate codes, while the architecture package decides
whether certified modes are worth deploying.
"""

from .faults import ErrorPattern, FaultDistribution, load_fault_distribution
from .verify import VerificationError, verify_code_document

__all__ = [
    "ErrorPattern",
    "FaultDistribution",
    "VerificationError",
    "load_fault_distribution",
    "verify_code_document",
]
