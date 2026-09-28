from __future__ import annotations

from typing import Optional


class PronunciationSeverityService:
    """
    Converts phonetic similarity and recognition evidence
    into an estimated pronunciation error severity.

    Severity is an interpretation layer.
    It does NOT claim that every detected substitution
    is a genuine pronunciation error.
    """

    def __init__(self) -> None:

        self.high_similarity_threshold = 0.80
        self.medium_similarity_threshold = 0.55

        self.high_confidence_threshold = 0.80
        self.medium_confidence_threshold = 0.60

    def classify(
        self,
        status: str,
        phonetic_similarity: Optional[float],
        expected_confidence: Optional[float],
        actual_confidence: Optional[float],
        evidence_status: Optional[str] = None,
        likely_error: bool = False,
    ) -> dict:

        if status == "match":
            return {
                "severity": None,
                "severity_score": 0.0,
                "severity_reason": "Phonemes match.",
            }

        if status == "deletion":
            return self._classify_deletion(
                actual_confidence=actual_confidence,
                evidence_status=evidence_status,
            )

        if status == "insertion":
            return self._classify_insertion(
                actual_confidence=actual_confidence,
                evidence_status=evidence_status,
            )

        if status != "substitution":
            return {
                "severity": "unknown",
                "severity_score": None,
                "severity_reason": "Unsupported alignment status.",
            }

        if phonetic_similarity is None:
            return {
                "severity": "unknown",
                "severity_score": None,
                "severity_reason": (
                    "Phonetic similarity is unavailable."
                ),
            }

        recognition_confidence = self._combined_confidence(
            expected_confidence,
            actual_confidence,
        )

        # --------------------------------------------------------------
        # Evidence uncertainty has priority.
        # --------------------------------------------------------------

        if evidence_status == "uncertain":
            return {
                "severity": "uncertain",
                "severity_score": None,
                "severity_reason": (
                    "Recognition evidence is too uncertain "
                    "to estimate pronunciation severity."
                ),
            }

        if recognition_confidence is not None:
            if recognition_confidence < self.medium_confidence_threshold:
                return {
                    "severity": "uncertain",
                    "severity_score": None,
                    "severity_reason": (
                        "Recognition confidence is too low."
                    ),
                }

        # --------------------------------------------------------------
        # Calculate raw severity from phonetic distance.
        # --------------------------------------------------------------

        distance = 1.0 - phonetic_similarity

        severity_score = round(
            distance * 100,
            2,
        )

        if phonetic_similarity >= self.high_similarity_threshold:
            severity = "mild"

        elif phonetic_similarity >= self.medium_similarity_threshold:
            severity = "moderate"

        else:
            severity = "severe"

        # --------------------------------------------------------------
        # If recognition itself is weak, don't overstate the result.
        # --------------------------------------------------------------

        if (
            recognition_confidence is not None
            and recognition_confidence < self.high_confidence_threshold
        ):
            if severity == "severe":
                severity = "moderate"

            severity_reason = (
                "Phonetic difference is detectable, but "
                "recognition confidence is not high enough "
                "to strongly assert severity."
            )

        else:
            severity_reason = (
                "Severity is estimated from phonetic distance "
                "with sufficient recognition confidence."
            )

        return {
            "severity": severity,
            "severity_score": severity_score,
            "severity_reason": severity_reason,
        }

    # ------------------------------------------------------------------
    # Deletion
    # ------------------------------------------------------------------

    def _classify_deletion(
        self,
        actual_confidence: Optional[float],
        evidence_status: Optional[str],
    ) -> dict:

        if evidence_status == "uncertain":
            return {
                "severity": "uncertain",
                "severity_score": None,
                "severity_reason": (
                    "Deletion evidence is uncertain."
                ),
            }

        confidence = actual_confidence

        if confidence is not None and confidence < 0.60:
            return {
                "severity": "uncertain",
                "severity_score": None,
                "severity_reason": (
                    "Recognition confidence is too low "
                    "to evaluate the deletion."
                ),
            }

        return {
            "severity": "severe",
            "severity_score": 100.0,
            "severity_reason": (
                "Expected phoneme was not detected in "
                "the user's pronunciation."
            ),
        }

    # ------------------------------------------------------------------
    # Insertion
    # ------------------------------------------------------------------

    def _classify_insertion(
        self,
        actual_confidence: Optional[float],
        evidence_status: Optional[str],
    ) -> dict:

        if evidence_status == "uncertain":
            return {
                "severity": "uncertain",
                "severity_score": None,
                "severity_reason": (
                    "Insertion evidence is uncertain."
                ),
            }

        confidence = actual_confidence

        if confidence is not None and confidence < 0.60:
            return {
                "severity": "uncertain",
                "severity_score": None,
                "severity_reason": (
                    "Recognition confidence is too low "
                    "to evaluate the insertion."
                ),
            }

        return {
            "severity": "moderate",
            "severity_score": 100.0,
            "severity_reason": (
                "An additional phoneme was detected "
                "in the user's pronunciation."
            ),
        }

    # ------------------------------------------------------------------
    # Confidence
    # ------------------------------------------------------------------

    @staticmethod
    def _combined_confidence(
        expected_confidence: Optional[float],
        actual_confidence: Optional[float],
    ) -> Optional[float]:

        values = [
            value
            for value in (
                expected_confidence,
                actual_confidence,
            )
            if value is not None
        ]

        if not values:
            return None

        # Conservative approach:
        # weakest side determines confidence.
        return min(values)