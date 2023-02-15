"""
Unit tests for the image registration engine.
"""

import pytest
from dataclasses import dataclass
from typing import Any, Optional

from image_registration import (
    ImageRegistrationEngine,
    AlgorithmBase,
    RegistrationResult,
    RegistrationError,
)
from image_registration.engine import EngineConfig, RegistrationOutput
from image_registration.exceptions import ConfigurationError


# Mock algorithm implementations for testing
class MockAlgorithm(AlgorithmBase):
    """Mock algorithm that returns a predefined result."""

    def __init__(self, name: str, result: Optional[RegistrationResult] = None):
        self._name = name
        self._result = result

    def align(self, src_img: Any, ref_img: Any) -> Optional[RegistrationResult]:
        return self._result

    @property
    def name(self) -> str:
        return self._name


class FailingAlgorithm(AlgorithmBase):
    """Mock algorithm that raises an exception."""

    def __init__(self, name: str = "FailingAlgo"):
        self._name = name

    def align(self, src_img: Any, ref_img: Any) -> Optional[RegistrationResult]:
        raise RuntimeError("Simulated algorithm failure")

    @property
    def name(self) -> str:
        return self._name


# Fixtures
@pytest.fixture
def good_result():
    """High-quality registration result that meets thresholds."""
    return RegistrationResult(
        score=0.92,
        inlier_ratio=0.75,
        homography=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],  # Mock identity matrix
        matches_count=150,
    )


@pytest.fixture
def mediocre_result():
    """Lower-quality result below default thresholds."""
    return RegistrationResult(
        score=0.70,
        inlier_ratio=0.45,
        homography=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        matches_count=80,
    )


@pytest.fixture
def poor_result():
    """Very poor result."""
    return RegistrationResult(
        score=0.40,
        inlier_ratio=0.20,
        homography=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
        matches_count=30,
    )


# Test RegistrationResult validation
class TestRegistrationResult:
    def test_valid_result(self, good_result):
        """Valid result should be created without error."""
        assert good_result.score == 0.92
        assert good_result.inlier_ratio == 0.75

    def test_invalid_score_above_one(self):
        """Score above 1.0 should raise ValueError."""
        with pytest.raises(ValueError, match="Score must be in"):
            RegistrationResult(
                score=1.5,
                inlier_ratio=0.5,
                homography=None,
                matches_count=100,
            )

    def test_invalid_score_below_zero(self):
        """Negative score should raise ValueError."""
        with pytest.raises(ValueError, match="Score must be in"):
            RegistrationResult(
                score=-0.1,
                inlier_ratio=0.5,
                homography=None,
                matches_count=100,
            )

    def test_invalid_inlier_ratio(self):
        """Invalid inlier ratio should raise ValueError."""
        with pytest.raises(ValueError, match="Inlier ratio must be in"):
            RegistrationResult(
                score=0.8,
                inlier_ratio=1.5,
                homography=None,
                matches_count=100,
            )

    def test_invalid_matches_count(self):
        """Negative matches count should raise ValueError."""
        with pytest.raises(ValueError, match="Matches count must be"):
            RegistrationResult(
                score=0.8,
                inlier_ratio=0.5,
                homography=None,
                matches_count=-10,
            )


# Test EngineConfig validation
class TestEngineConfig:
    def test_default_config(self):
        """Default config should have expected values."""
        config = EngineConfig()
        assert config.min_score == 0.85
        assert config.min_inlier_ratio == 0.6
        assert config.enable_fallback is True

    def test_custom_config(self):
        """Custom config values should be accepted."""
        config = EngineConfig(min_score=0.9, min_inlier_ratio=0.7, enable_fallback=False)
        assert config.min_score == 0.9
        assert config.min_inlier_ratio == 0.7
        assert config.enable_fallback is False

    def test_invalid_min_score(self):
        """Invalid min_score should raise ValueError."""
        with pytest.raises(ValueError, match="min_score must be in"):
            EngineConfig(min_score=1.5)

    def test_invalid_min_inlier_ratio(self):
        """Invalid min_inlier_ratio should raise ValueError."""
        with pytest.raises(ValueError, match="min_inlier_ratio must be in"):
            EngineConfig(min_inlier_ratio=-0.1)


# Test ImageRegistrationEngine
class TestImageRegistrationEngine:
    def test_engine_requires_algorithms(self):
        """Engine should reject empty algorithm dict."""
        with pytest.raises(ConfigurationError, match="At least one algorithm"):
            ImageRegistrationEngine(algorithms={})

    def test_single_algorithm_success(self, good_result):
        """Single algorithm producing good result should succeed."""
        algo = MockAlgorithm("SIFT", good_result)
        engine = ImageRegistrationEngine(algorithms={"SIFT": algo})

        output = engine.register(src_img=None, ref_img=None)

        assert output.algorithm == "SIFT"
        assert output.status == "accepted"
        assert output.result.score == 0.92
        assert "SIFT" in output.attempts

    def test_multiple_algorithms_first_succeeds(self, good_result, mediocre_result):
        """If first algorithm succeeds, others should not be tried."""
        algo1 = MockAlgorithm("SIFT", good_result)
        algo2 = MockAlgorithm("ORB", mediocre_result)

        engine = ImageRegistrationEngine(algorithms={"SIFT": algo1, "ORB": algo2})
        output = engine.register(src_img=None, ref_img=None)

        assert output.algorithm == "SIFT"
        assert output.status == "accepted"
        assert output.attempts == ["SIFT"]  # Early exit, ORB not tried

    def test_fallback_to_second_algorithm(self, mediocre_result, good_result):
        """If first algorithm fails threshold, should try second."""
        algo1 = MockAlgorithm("ORB", mediocre_result)
        algo2 = MockAlgorithm("SIFT", good_result)

        # Use OrderedDict-like behavior (Python 3.7+ dicts are ordered)
        engine = ImageRegistrationEngine(algorithms={"ORB": algo1, "SIFT": algo2})
        output = engine.register(src_img=None, ref_img=None)

        assert output.algorithm == "SIFT"
        assert output.status == "accepted"
        assert output.attempts == ["ORB", "SIFT"]

    def test_fallback_low_confidence(self, mediocre_result, poor_result):
        """When no algorithm meets threshold, return best with fallback status."""
        algo1 = MockAlgorithm("ORB", poor_result)
        algo2 = MockAlgorithm("SIFT", mediocre_result)

        engine = ImageRegistrationEngine(algorithms={"ORB": algo1, "SIFT": algo2})
        output = engine.register(src_img=None, ref_img=None)

        assert output.algorithm == "SIFT"  # Better of the two
        assert output.status == "fallback_low_confidence"
        assert output.result.score == 0.70

    def test_no_valid_homography_raises(self):
        """When all algorithms return None, should raise RegistrationError."""
        algo1 = MockAlgorithm("SIFT", None)
        algo2 = MockAlgorithm("ORB", None)

        engine = ImageRegistrationEngine(algorithms={"SIFT": algo1, "ORB": algo2})

        with pytest.raises(RegistrationError, match="No alignment produced a valid homography"):
            engine.register(src_img=None, ref_img=None)

    def test_fallback_disabled_raises(self, mediocre_result):
        """With fallback disabled, should raise if thresholds not met."""
        algo = MockAlgorithm("SIFT", mediocre_result)
        config = EngineConfig(enable_fallback=False)

        engine = ImageRegistrationEngine(algorithms={"SIFT": algo}, config=config)

        with pytest.raises(RegistrationError, match="No alignment met quality thresholds"):
            engine.register(src_img=None, ref_img=None)

    def test_algorithm_exception_handled(self, good_result):
        """Exception from one algorithm should not prevent trying others."""
        algo1 = FailingAlgorithm("FailAlgo")
        algo2 = MockAlgorithm("SIFT", good_result)

        engine = ImageRegistrationEngine(algorithms={"FailAlgo": algo1, "SIFT": algo2})
        output = engine.register(src_img=None, ref_img=None)

        assert output.algorithm == "SIFT"
        assert output.status == "accepted"

    def test_all_algorithms_fail_raises(self):
        """When all algorithms raise exceptions, should raise RegistrationError."""
        algo1 = FailingAlgorithm("Fail1")
        algo2 = FailingAlgorithm("Fail2")

        engine = ImageRegistrationEngine(algorithms={"Fail1": algo1, "Fail2": algo2})

        with pytest.raises(RegistrationError, match="No alignment produced a valid homography"):
            engine.register(src_img=None, ref_img=None)

    def test_custom_thresholds(self):
        """Custom thresholds should be respected."""
        result = RegistrationResult(
            score=0.75,
            inlier_ratio=0.65,
            homography=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            matches_count=100,
        )

        algo = MockAlgorithm("SIFT", result)
        config = EngineConfig(min_score=0.70, min_inlier_ratio=0.60)

        engine = ImageRegistrationEngine(algorithms={"SIFT": algo}, config=config)
        output = engine.register(src_img=None, ref_img=None)

        assert output.status == "accepted"

    def test_register_algorithm_dynamically(self, good_result):
        """Should allow dynamic algorithm registration."""
        algo1 = MockAlgorithm("SIFT", None)
        engine = ImageRegistrationEngine(algorithms={"SIFT": algo1})

        algo2 = MockAlgorithm("ORB", good_result)
        engine.register_algorithm("ORB", algo2)

        assert "ORB" in engine.algorithms
        assert len(engine.algorithms) == 2

    def test_unregister_algorithm(self, good_result):
        """Should allow removing algorithms."""
        algo1 = MockAlgorithm("SIFT", good_result)
        algo2 = MockAlgorithm("ORB", good_result)

        engine = ImageRegistrationEngine(algorithms={"SIFT": algo1, "ORB": algo2})
        engine.unregister_algorithm("ORB")

        assert "ORB" not in engine.algorithms
        assert len(engine.algorithms) == 1

    def test_cannot_remove_last_algorithm(self, good_result):
        """Should not allow removing the last algorithm."""
        algo = MockAlgorithm("SIFT", good_result)
        engine = ImageRegistrationEngine(algorithms={"SIFT": algo})

        with pytest.raises(ConfigurationError, match="Cannot remove the last algorithm"):
            engine.unregister_algorithm("SIFT")

    def test_result_metadata_preserved(self):
        """Algorithm-specific metadata should be preserved in result."""
        result = RegistrationResult(
            score=0.90,
            inlier_ratio=0.70,
            homography=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            matches_count=120,
            metadata={"keypoints": 250, "descriptor_type": "SIFT"},
        )

        algo = MockAlgorithm("SIFT", result)
        engine = ImageRegistrationEngine(algorithms={"SIFT": algo})
        output = engine.register(src_img=None, ref_img=None)

        assert output.result.metadata == {"keypoints": 250, "descriptor_type": "SIFT"}


# Edge case tests
class TestEdgeCases:
    def test_exact_threshold_values(self):
        """Result exactly at threshold should be accepted."""
        result = RegistrationResult(
            score=0.85,  # Exactly at default threshold
            inlier_ratio=0.6,  # Exactly at default threshold
            homography=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            matches_count=100,
        )

        algo = MockAlgorithm("SIFT", result)
        engine = ImageRegistrationEngine(algorithms={"SIFT": algo})
        output = engine.register(src_img=None, ref_img=None)

        assert output.status == "accepted"

    def test_score_above_inlier_below_threshold(self):
        """High score but low inlier ratio should not be accepted."""
        result = RegistrationResult(
            score=0.95,
            inlier_ratio=0.30,  # Below threshold
            homography=[[1, 0, 0], [0, 1, 0], [0, 0, 1]],
            matches_count=100,
        )

        algo = MockAlgorithm("SIFT", result)
        engine = ImageRegistrationEngine(algorithms={"SIFT": algo})
        output = engine.register(src_img=None, ref_img=None)

        assert output.status == "fallback_low_confidence"

    def test_zero_matches(self):
        """Result with zero matches should be handled."""
        result = RegistrationResult(
            score=0.0,
            inlier_ratio=0.0,
            homography=None,
            matches_count=0,
        )

        algo = MockAlgorithm("SIFT", result)
        engine = ImageRegistrationEngine(algorithms={"SIFT": algo})
        output = engine.register(src_img=None, ref_img=None)

        assert output.status == "fallback_low_confidence"
        assert output.result.matches_count == 0






