"""
Multi-algorithm image registration engine with intelligent fallback.

This module implements a production-grade image registration system designed for
safety-critical applications (exam processing). The key innovation is a strategy
pattern that automatically tries multiple feature-based alignment algorithms,
scores their results, and provides graceful degradation when preferred methods fail.

Core Innovation:
    - Multi-algorithm fallback: Automatically tries alternative algorithms when
      primary methods fail or produce low-confidence results
    - Quality gates: Configurable thresholds (min_score, min_inlier_ratio) enforce
      acceptable alignment quality before downstream processing
    - Observable behavior: Comprehensive logging at all decision points for audit
      and debugging in production environments

Typical Usage:
    >>> from image_registration import ImageRegistrationEngine, EngineConfig
    >>> config = EngineConfig(min_score=0.85, min_inlier_ratio=0.6)
    >>> engine = ImageRegistrationEngine(algorithms={"SIFT": SIFTAlgorithm()}, config=config)
    >>> output = engine.register(src_image, ref_image)
    >>> if output.status == "accepted":
    ...     aligned = apply_homography(src_image, output.result.homography)

Classes:
    EngineConfig: Configuration for quality thresholds and fallback behavior
    RegistrationOutput: Output container with algorithm name, status, and result
    ImageRegistrationEngine: Main orchestrator for multi-algorithm registration
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from .algorithms import AlgorithmBase, RegistrationResult
from .exceptions import RegistrationError, ConfigurationError


logger = logging.getLogger(__name__)


@dataclass
class EngineConfig:
    """
    Configuration for the registration engine.
    
    Attributes:
        min_score: Minimum score threshold for accepting an alignment (0.0 to 1.0).
        min_inlier_ratio: Minimum inlier ratio for accepting an alignment (0.0 to 1.0).
        enable_fallback: If True, return best available result even if below thresholds.
    """
    min_score: float = 0.85
    min_inlier_ratio: float = 0.6
    enable_fallback: bool = True

    def __post_init__(self):
        """Validate configuration values."""
        if not 0.0 <= self.min_score <= 1.0:
            raise ValueError(f"min_score must be in [0.0, 1.0], got {self.min_score}")
        if not 0.0 <= self.min_inlier_ratio <= 1.0:
            raise ValueError(f"min_inlier_ratio must be in [0.0, 1.0], got {self.min_inlier_ratio}")


@dataclass
class RegistrationOutput:
    """
    Final output from the registration engine.
    
    Attributes:
        algorithm: Name of the algorithm that produced this result.
        status: 'accepted' if thresholds met, 'fallback_low_confidence' if using best available.
        result: The underlying RegistrationResult.
        attempts: List of algorithm names attempted, in order.
    """
    algorithm: str
    status: str
    result: RegistrationResult
    attempts: List[str] = field(default_factory=list)


class ImageRegistrationEngine:
    """
    Multi-algorithm image registration engine.
    
    Attempts registration with multiple feature-based algorithms (SIFT, ORB, AKAZE, BRISK, etc.),
    scores each result, and returns the best alignment with confidence status.
    
    Algorithms are tried in the order registered. Early exit occurs when a result
    meets the configured quality thresholds.
    """

    def __init__(
        self,
        algorithms: Dict[str, AlgorithmBase],
        config: Optional[EngineConfig] = None,
        logger_override: Optional[logging.Logger] = None,
    ):
        """
        Initialize the registration engine.
        
        Args:
            algorithms: Dictionary mapping algorithm names to AlgorithmBase instances.
                        Example: {"SIFT": SIFTAlgorithm(), "ORB": ORBAlgorithm()}
            config: Engine configuration. Uses defaults if not provided.
            logger_override: Optional logger instance. Uses module logger if not provided.
            
        Raises:
            ConfigurationError: If algorithms dict is empty.
        """
        if not algorithms:
            raise ConfigurationError("At least one algorithm must be provided")

        self.algorithms = algorithms
        self.config = config or EngineConfig()
        self.logger = logger_override or logger

    def register(
        self,
        src_img: Any,
        ref_img: Any,
    ) -> RegistrationOutput:
        """
        Register source image to reference image using multiple algorithms.
        
        Tries each algorithm in order until one produces a result meeting the
        quality thresholds (min_score and min_inlier_ratio). If no algorithm
        meets thresholds, returns the best available result with 'fallback_low_confidence'
        status (if fallback enabled), or raises RegistrationError.
        
        Args:
            src_img: Source image to align.
            ref_img: Reference image to align to.
            
        Returns:
            RegistrationOutput with algorithm name, status, and result.
            
        Raises:
            RegistrationError: If no algorithm produces a valid homography and fallback is disabled.
        """
        best_result: Optional[RegistrationResult] = None
        best_algorithm: Optional[str] = None
        attempts: List[str] = []

        self.logger.info(f"Starting registration with {len(self.algorithms)} algorithms")

        for name, algo in self.algorithms.items():
            attempts.append(name)
            self.logger.debug(f"Attempting algorithm: {name}")

            try:
                result = algo.align(src_img, ref_img)
            except Exception as e:
                self.logger.warning(f"Algorithm {name} raised exception: {e}")
                continue

            if result is None:
                self.logger.debug(f"Algorithm {name} returned None (no valid alignment)")
                continue

            self.logger.debug(
                f"Algorithm {name}: score={result.score:.3f}, "
                f"inlier_ratio={result.inlier_ratio:.3f}, "
                f"matches={result.matches_count}"
            )

            # Track best result seen so far
            if best_result is None or result.score > best_result.score:
                best_result = result
                best_algorithm = name

            # Check if this result meets acceptance criteria
            if self._is_acceptable(result):
                self.logger.info(
                    f"Accepted result from {name} (score={result.score:.3f}, "
                    f"inlier_ratio={result.inlier_ratio:.3f})"
                )
                return RegistrationOutput(
                    algorithm=name,
                    status="accepted",
                    result=result,
                    attempts=attempts,
                )

        # No algorithm met thresholds - fallback logic
        if best_result is None:
            self.logger.error("No algorithm produced a valid homography")
            raise RegistrationError(
                f"No alignment produced a valid homography. Attempted: {', '.join(attempts)}"
            )

        if not self.config.enable_fallback:
            self.logger.error(
                f"Best result from {best_algorithm} did not meet thresholds and fallback is disabled"
            )
            raise RegistrationError(
                f"No alignment met quality thresholds (min_score={self.config.min_score}, "
                f"min_inlier_ratio={self.config.min_inlier_ratio}). "
                f"Best score: {best_result.score:.3f} from {best_algorithm}"
            )

        self.logger.warning(
            f"Using fallback result from {best_algorithm} with score={best_result.score:.3f} "
            f"(below threshold={self.config.min_score})"
        )

        # best_algorithm is guaranteed to be set if best_result is not None
        assert best_algorithm is not None

        return RegistrationOutput(
            algorithm=best_algorithm,
            status="fallback_low_confidence",
            result=best_result,
            attempts=attempts,
        )

    def _is_acceptable(self, result: RegistrationResult) -> bool:
        """Check if a result meets acceptance thresholds."""
        return (
            result.score >= self.config.min_score
            and result.inlier_ratio >= self.config.min_inlier_ratio
        )

    def register_algorithm(self, name: str, algorithm: AlgorithmBase) -> None:
        """
        Dynamically register a new algorithm.
        
        Args:
            name: Algorithm name.
            algorithm: AlgorithmBase instance.
        """
        self.logger.info(f"Registering new algorithm: {name}")
        self.algorithms[name] = algorithm

    def unregister_algorithm(self, name: str) -> None:
        """
        Remove an algorithm from the engine.
        
        Args:
            name: Algorithm name to remove.
            
        Raises:
            ConfigurationError: If trying to remove the last algorithm.
        """
        if len(self.algorithms) == 1:
            raise ConfigurationError("Cannot remove the last algorithm")
        
        if name in self.algorithms:
            self.logger.info(f"Unregistering algorithm: {name}")
            del self.algorithms[name]


