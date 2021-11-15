"""
Exceptions for the image registration engine.
"""


class RegistrationError(Exception):
    """Base exception for registration failures."""
    pass


class AlgorithmError(RegistrationError):
    """Raised when an algorithm fails to produce a valid result."""
    pass


class ConfigurationError(RegistrationError):
    """Raised when the engine is misconfigured."""
    pass

