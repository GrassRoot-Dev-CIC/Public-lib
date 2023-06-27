# Image Registration Engine

Multi-algorithm image registration for high-volume exam script processing.

## Innovation Highlights

- **Multi-Algorithm Strategy**: Runtime composition of feature detection algorithms (SIFT, ORB, AKAZE) with automatic fallback chains
- **Quality Scoring System**: Quantitative alignment confidence (0.0–1.0) with configurable thresholds for safety-critical applications
- **Plugin Architecture**: Dynamic algorithm registration/unregistration enables extensibility without core changes
- **Intelligent Fallback**: Automatic degradation through algorithm chain until quality thresholds are met or all options exhausted

## Overview

This library provides a production-ready image registration engine that:
- Supports multiple feature-based algorithms (SIFT, ORB, AKAZE, BRISK, etc.)
- Automatically scores alignment quality and selects the best result
- Provides fallback logic with confidence flagging
- Allows dynamic algorithm registration (plugin-style architecture)
- Includes comprehensive logging hooks

## Installation

```bash
# Install from local directory
pip install -e .

# For testing
pip install pytest
```

## Quick Start

```python
from image_registration import ImageRegistrationEngine, AlgorithmBase, RegistrationResult
import cv2
import numpy as np

# 1. Implement your algorithm (example with OpenCV SIFT)
class SIFTAlgorithm(AlgorithmBase):
    def __init__(self):
        # Initialize your SIFT detector (e.g., cv2.SIFT_create())
        # See examples_opencv.py for reference implementation
        pass
    
    def align(self, src_img, ref_img):
        # Implement SIFT-based alignment
        # See examples_opencv.py for reference implementation
        # - Detect keypoints and compute descriptors
        # - Match features between images
        # - Compute homography using RANSAC
        # - Return RegistrationResult or None
        
        # Example structure:
        # matches = match_features(src_img, ref_img)
        # homography, inliers = compute_homography(matches)
        # score = compute_alignment_score(inliers, matches)
        
        return RegistrationResult(
            score=0.92,
            inlier_ratio=0.75,
            homography=homography,
            matches_count=len(matches)
        )

# 2. Create engine with multiple algorithms
algorithms = {
    "SIFT": SIFTAlgorithm(),   # See examples_opencv.py for implementation
    "ORB": ORBAlgorithm(),     # See examples_opencv.py for implementation
    "AKAZE": AKAZEAlgorithm(), # See examples_opencv.py for implementation
}

engine = ImageRegistrationEngine(algorithms=algorithms)

# 3. Register images
src_image = cv2.imread("exam_page_scanned.jpg")
ref_image = cv2.imread("exam_page_template.jpg")

output = engine.register(src_image, ref_image)

print(f"Algorithm: {output.algorithm}")
print(f"Status: {output.status}")
print(f"Score: {output.result.score:.3f}")
print(f"Inlier ratio: {output.result.inlier_ratio:.3f}")

if output.status == "accepted":
    # Use the homography for image warping
    aligned = cv2.warpPerspective(src_image, output.result.homography, ...)
else:
    # Handle low-confidence alignment
    print("Warning: Low confidence alignment")
```

## Configuration

```python
from image_registration.engine import EngineConfig

# Custom thresholds
config = EngineConfig(
    min_score=0.90,           # Minimum quality score (0.0 to 1.0)
    min_inlier_ratio=0.70,    # Minimum inlier ratio (0.0 to 1.0)
    enable_fallback=True      # Return best result even if below thresholds
)

engine = ImageRegistrationEngine(algorithms=algorithms, config=config)
```

## Dynamic Algorithm Registration

```python
# Add algorithm at runtime
engine.register_algorithm("BRISK", BRISKAlgorithm())

# Remove algorithm
engine.unregister_algorithm("ORB")
```

## Logging

The engine uses Python's standard `logging` module:

```python
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("image_registration")

# Or inject a custom logger
engine = ImageRegistrationEngine(
    algorithms=algorithms,
    logger_override=my_custom_logger
)
```

## Testing

```bash
pytest image_registration/tests/
```

## Architecture

```
image_registration/
├── __init__.py           # Public API exports
├── engine.py             # Main ImageRegistrationEngine class
├── algorithms.py         # AlgorithmBase interface and RegistrationResult
├── exceptions.py         # Custom exceptions
└── tests/
    └── test_engine.py    # Comprehensive unit tests
```

## Algorithm Implementation Guide

To implement a new algorithm, subclass `AlgorithmBase`:

```python
from image_registration import AlgorithmBase, RegistrationResult
from typing import Any, Optional

class MyCustomAlgorithm(AlgorithmBase):
    def align(self, src_img: Any, ref_img: Any) -> Optional[RegistrationResult]:
        """
        Perform feature-based alignment.
        
        Should:
        1. Detect features in both images
        2. Match features
        3. Compute homography (e.g., using RANSAC)
        4. Calculate quality metrics (score, inlier_ratio)
        5. Return RegistrationResult or None if alignment fails
        
        Catch exceptions internally and return None rather than raising.
        """
        try:
            # Your implementation here
            # ...
            
            return RegistrationResult(
                score=computed_score,
                inlier_ratio=num_inliers / total_matches,
                homography=H,  # 3x3 transformation matrix
                matches_count=len(matches),
                metadata={"custom_field": "value"}  # Optional
            )
        except Exception as e:
            # Log error if needed, return None for graceful fallback
            return None
```

## Design Principles

1. **No external dependencies**: Core library uses only Python stdlib. Algorithms implementations (SIFT, ORB, etc.) are user-provided.

2. **Plugin architecture**: Algorithms can be registered/unregistered dynamically.

3. **Deterministic and testable**: No global state, clear separation of concerns.

4. **Graceful degradation**: Failed algorithms don't crash the engine; it tries alternatives.

5. **Observable**: Comprehensive logging at INFO, DEBUG, WARNING, ERROR levels.

6. **Type-safe**: Full type hints for better IDE support and early error detection.

## Integration Points

This library defines a clean interface for image registration. For production deployment:

- **Algorithm implementations**: Implement `AlgorithmBase` for your chosen feature detectors (SIFT, ORB, AKAZE, BRISK, or custom algorithms). The `examples_opencv.py` file provides reference implementations using OpenCV.

- **Persistence**: Extend with caching, audit logging, or performance metrics collection as needed.

- **Image preprocessing**: Add optional preprocessing hooks for grayscale conversion, histogram equalization, noise reduction, or resolution normalization.

## License

Internal use - AQA assessment technology platform.


