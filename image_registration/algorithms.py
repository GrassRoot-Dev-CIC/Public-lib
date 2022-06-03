"""
Abstract base class and data models for image registration algorithms.

This module defines the contract that all registration algorithms must implement,
enabling the strategy pattern used by ImageRegistrationEngine. The key innovation
is the separation of algorithm implementation from orchestration logic, allowing
zero-modification extensibility.

Classes:
    RegistrationResult: Immutable value object containing alignment quality metrics
    AlgorithmBase: Abstract interface for feature-based registration algorithms

Design Pattern:
    Strategy pattern - algorithms are interchangeable plugins that implement a
    common interface. The engine orchestrates execution and scoring without knowing
    implementation details.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional
from dataclasses import dataclass


@dataclass
class RegistrationResult:
    """
    Container for registration algorithm output.
    
    Attributes:
        score: Quality score (0.0 to 1.0) of the alignment.
        inlier_ratio: Ratio of inlier matches to total matches.
        homography: Transformation matrix (e.g., 3x3 numpy array).
                    Type is Any to avoid forcing numpy dependency.
        matches_count: Number of feature matches found.
        metadata: Optional algorithm-specific data.
    """
    score: float
    inlier_ratio: float
    homography: Any
    matches_count: int
    metadata: Optional[dict] = None

    def __post_init__(self):
        """Validate result fields."""
        if not 0.0 <= self.score <= 1.0:
            raise ValueError(f"Score must be in [0.0, 1.0], got {self.score}")
        if not 0.0 <= self.inlier_ratio <= 1.0:
            raise ValueError(f"Inlier ratio must be in [0.0, 1.0], got {self.inlier_ratio}")
        if self.matches_count < 0:
            raise ValueError(f"Matches count must be >= 0, got {self.matches_count}")


class AlgorithmBase(ABC):
    """
    Abstract base class for registration algorithms.
    
    Subclasses must implement the align() method to perform feature-based
    image registration.
    """

    @abstractmethod
    def align(self, src_img: Any, ref_img: Any) -> Optional[RegistrationResult]:
        """
        Align source image to reference image.
        
        Args:
            src_img: Source image (type depends on implementation, e.g., numpy array).
            ref_img: Reference image.
            
        Returns:
            RegistrationResult if alignment succeeds, None if no valid homography found.
            
        Note:
            Implementations should catch internal exceptions and return None
            rather than raising, to allow graceful fallback to other algorithms.
        """
        pass

    @property
    def name(self) -> str:
        """Return algorithm name for logging and reporting."""
        return self.__class__.__name__



