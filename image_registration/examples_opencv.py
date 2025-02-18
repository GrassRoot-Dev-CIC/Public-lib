"""
Example algorithm implementations (reference only - requires OpenCV).

These are NOT included in the core library to avoid external dependencies.
Copy and adapt as needed for your use case.
"""

# NOTE: Requires opencv-python (pip install opencv-python)
# This file is for reference only and is not part of the library

import cv2
import numpy as np
from typing import Any, Optional

from image_registration import AlgorithmBase, RegistrationResult


class SIFTAlgorithm(AlgorithmBase):
    """
    SIFT (Scale-Invariant Feature Transform) based registration.
    
    Requires: opencv-contrib-python or opencv-python with SIFT support
    """

    def __init__(self, n_features: int = 0, n_octave_layers: int = 3):
        """
        Args:
            n_features: Number of best features to retain (0 = all).
            n_octave_layers: Number of layers in each octave.
        """
        self.detector = cv2.SIFT_create(
            nfeatures=n_features,
            nOctaveLayers=n_octave_layers,
        )
        self.matcher = cv2.BFMatcher(cv2.NORM_L2, crossCheck=False)

    def align(self, src_img: np.ndarray, ref_img: np.ndarray) -> Optional[RegistrationResult]:
        """Perform SIFT-based alignment."""
        try:
            # Convert to grayscale if needed
            src_gray = cv2.cvtColor(src_img, cv2.COLOR_BGR2GRAY) if len(src_img.shape) == 3 else src_img
            ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY) if len(ref_img.shape) == 3 else ref_img

            # Detect keypoints and compute descriptors
            kp1, desc1 = self.detector.detectAndCompute(src_gray, None)
            kp2, desc2 = self.detector.detectAndCompute(ref_gray, None)

            if desc1 is None or desc2 is None or len(kp1) < 4 or len(kp2) < 4:
                return None

            # Match features
            matches = self.matcher.knnMatch(desc1, desc2, k=2)

            # Apply Lowe's ratio test
            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < 0.75 * n.distance:
                        good_matches.append(m)

            if len(good_matches) < 4:
                return None

            # Extract matched keypoint coordinates
            src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            ref_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

            # Compute homography with RANSAC
            H, mask = cv2.findHomography(src_pts, ref_pts, cv2.RANSAC, 5.0)

            if H is None:
                return None

            # Calculate metrics
            inliers = np.sum(mask)
            inlier_ratio = inliers / len(good_matches)

            # Simple scoring: weighted combination of inlier ratio and match count
            match_score = min(len(good_matches) / 100.0, 1.0)  # Normalize to [0,1]
            score = 0.7 * inlier_ratio + 0.3 * match_score

            return RegistrationResult(
                score=score,
                inlier_ratio=inlier_ratio,
                homography=H.tolist(),  # Convert to list for JSON serialization
                matches_count=len(good_matches),
                metadata={
                    "total_keypoints_src": len(kp1),
                    "total_keypoints_ref": len(kp2),
                    "inliers": int(inliers),
                },
            )

        except Exception:
            # Graceful failure - let engine try other algorithms
            return None


class ORBAlgorithm(AlgorithmBase):
    """
    ORB (Oriented FAST and Rotated BRIEF) based registration.
    
    Faster than SIFT but may be less accurate.
    """

    def __init__(self, n_features: int = 500):
        """
        Args:
            n_features: Maximum number of features to detect.
        """
        self.detector = cv2.ORB_create(nfeatures=n_features)
        self.matcher = cv2.BFMatcher(cv2.NORM_HAMMING, crossCheck=False)

    def align(self, src_img: np.ndarray, ref_img: np.ndarray) -> Optional[RegistrationResult]:
        """Perform ORB-based alignment."""
        try:
            src_gray = cv2.cvtColor(src_img, cv2.COLOR_BGR2GRAY) if len(src_img.shape) == 3 else src_img
            ref_gray = cv2.cvtColor(ref_img, cv2.COLOR_BGR2GRAY) if len(ref_img.shape) == 3 else ref_img

            kp1, desc1 = self.detector.detectAndCompute(src_gray, None)
            kp2, desc2 = self.detector.detectAndCompute(ref_gray, None)

            if desc1 is None or desc2 is None or len(kp1) < 4 or len(kp2) < 4:
                return None

            matches = self.matcher.knnMatch(desc1, desc2, k=2)

            good_matches = []
            for match_pair in matches:
                if len(match_pair) == 2:
                    m, n = match_pair
                    if m.distance < 0.75 * n.distance:
                        good_matches.append(m)

            if len(good_matches) < 4:
                return None

            src_pts = np.float32([kp1[m.queryIdx].pt for m in good_matches]).reshape(-1, 1, 2)
            ref_pts = np.float32([kp2[m.trainIdx].pt for m in good_matches]).reshape(-1, 1, 2)

            H, mask = cv2.findHomography(src_pts, ref_pts, cv2.RANSAC, 5.0)

            if H is None:
                return None

            inliers = np.sum(mask)
            inlier_ratio = inliers / len(good_matches)
            match_score = min(len(good_matches) / 100.0, 1.0)
            score = 0.7 * inlier_ratio + 0.3 * match_score

            return RegistrationResult(
                score=score,
                inlier_ratio=inlier_ratio,
                homography=H.tolist(),
                matches_count=len(good_matches),
                metadata={
                    "total_keypoints_src": len(kp1),
                    "total_keypoints_ref": len(kp2),
                    "inliers": int(inliers),
                },
            )

        except Exception:
            return None


# Usage example:
if __name__ == "__main__":
    from image_registration import ImageRegistrationEngine

    algorithms = {
        "SIFT": SIFTAlgorithm(),
        "ORB": ORBAlgorithm(),
    }

    engine = ImageRegistrationEngine(algorithms=algorithms)

    # Load test images
    src = cv2.imread("test_src.jpg")
    ref = cv2.imread("test_ref.jpg")

    if src is not None and ref is not None:
        output = engine.register(src, ref)
        print(f"Algorithm: {output.algorithm}")
        print(f"Status: {output.status}")
        print(f"Score: {output.result.score:.3f}")
    else:
        print("Test images not found")





