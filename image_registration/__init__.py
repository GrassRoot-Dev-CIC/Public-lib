"""
Image Registration Engine for high-volume exam script processing.

Multi-algorithm registration with automatic scoring, fallback, and confidence flagging.
"""

from .engine import ImageRegistrationEngine
from .algorithms import AlgorithmBase, RegistrationResult
from .exceptions import RegistrationError, AlgorithmError

__all__ = [
    'ImageRegistrationEngine',
    'AlgorithmBase',
    'RegistrationResult',
    'RegistrationError',
    'AlgorithmError',
]

__version__ = '1.0.0'
