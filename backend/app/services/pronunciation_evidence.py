from __future__ import annotations


class PronunciationEvidenceService:
    """
    Analyze phoneme alignment results and produce pronunciation evidence.

    This service does NOT directly claim that a phoneme substitution
    is a pronunciation error.

    It combines:
    - alignment status
    - reference confidence
    - user confidence

    to estimate how trustworthy the detected difference is.
    """

    # =========================================================
    # Initialization
    # =========================================================

    def __init__(
        self,
        high_confidence_threshold: float = 0.80,
        medium_confidence_threshold: float = 0.60,
    ):
        self.high_confidence_threshold = high_confidence_threshold

        self.medium_confidence_threshold = medium_confidence_threshold

    # =========================================================
    # Confidence helpers
    # =========================================================

    @staticmethod
    def _normalize_confidence(
        confidence: float | None,
    ) -> float | None:

        if confidence is None:
            return None

        try:
            confidence = float(confidence)
        except (TypeError, ValueError):
            return None

        return max(
            0.0,
            min(
                confidence,
                1.0,
            ),
        )

    def _confidence_level(
        self,
        confidence: float | None,
    ) -> str:

        if confidence is None:
            return "unknown"

        if confidence >= self.high_confidence_threshold:
            return "high"

        if confidence >= self.medium_confidence_threshold:
            return "medium"

        return "low"

    # =========================================================
    # Main analysis
    # =========================================================

    def analyze(
        self,
        alignment_result: dict,
    ) -> dict:

        alignment = alignment_result.get(
            "alignment",
            [],
        )

        evidence = []

        for item in alignment:

            evidence_item = self._analyze_item(item)

            evidence.append(evidence_item)

        summary = self._build_summary(evidence)

        return {
            "evidence": evidence,
            "summary": summary,
        }

    # =========================================================
    # Analyze one alignment item
    # =========================================================

    def _analyze_item(
        self,
        item: dict,
    ) -> dict:

        status = item.get("status")

        expected = item.get("expected")

        actual = item.get("actual")

        expected_confidence = self._normalize_confidence(
            item.get("expected_confidence")
        )

        actual_confidence = self._normalize_confidence(item.get("actual_confidence"))

        # -----------------------------------------------------
        # MATCH
        # -----------------------------------------------------

        if status == "match":

            return {
                **item,
                "evidence_status": (self._match_evidence_status(expected_confidence, actual_confidence,)),
                "confidence_level": (
                    self._match_confidence_level(
                        expected_confidence,
                        actual_confidence,
                    )
                ),
                "likely_error": False,
                "reason": (
                    self._match_reason(
                        expected_confidence,
                        actual_confidence,
                    )
                ),
            }

        # -----------------------------------------------------
        # SUBSTITUTION
        # -----------------------------------------------------

        if status == "substitution":

            return {
                **item,
                "evidence_status": (
                    self._substitution_evidence_status(
                        expected_confidence,
                        actual_confidence,
                    )
                ),
                "confidence_level": (
                    self._substitution_confidence_level(
                        expected_confidence,
                        actual_confidence,
                    )
                ),
                "likely_error": (
                    self._is_likely_substitution_error(
                        expected_confidence,
                        actual_confidence,
                    )
                ),
                "reason": (
                    self._substitution_reason(
                        expected,
                        actual,
                        expected_confidence,
                        actual_confidence,
                    )
                ),
            }

        # -----------------------------------------------------
        # DELETION
        # -----------------------------------------------------

        if status == "deletion":

            return {
                **item,
                "evidence_status": "possible_error",
                "confidence_level": (self._confidence_level(expected_confidence)),
                "likely_error": (
                    expected_confidence is None
                    or expected_confidence >= self.medium_confidence_threshold
                ),
                "reason": (
                    f"Reference phoneme "
                    f"'{expected}' was not detected "
                    f"in the user speech."
                ),
            }

        # -----------------------------------------------------
        # INSERTION
        # -----------------------------------------------------

        if status == "insertion":

            return {
                **item,
                "evidence_status": "possible_error",
                "confidence_level": (self._confidence_level(actual_confidence)),
                "likely_error": (
                    actual_confidence is None
                    or actual_confidence >= self.medium_confidence_threshold
                ),
                "reason": (
                    f"User produced phoneme "
                    f"'{actual}' which is not present "
                    f"in the reference at this alignment point."
                ),
            }

        # -----------------------------------------------------
        # UNKNOWN
        # -----------------------------------------------------

        return {
            **item,
            "evidence_status": "unknown",
            "confidence_level": "unknown",
            "likely_error": False,
            "reason": "Unknown alignment status.",
        }

    # =========================================================
    # Match evidence
    # =========================================================

    def _match_confidence_level(
        self,
        expected_confidence: float | None,
        actual_confidence: float | None,
    ) -> str:
    
        confidences = [
            confidence
            for confidence in (
                expected_confidence,
                actual_confidence,
            )
            if confidence is not None
        ]
    
        if not confidences:
            return "unknown"
    
        combined_confidence = min(
            confidences
        )
    
        return self._confidence_level(
            combined_confidence
        )

    def _match_evidence_status(
        self,
        expected_confidence: float | None,
        actual_confidence: float | None,
    ) -> str:

        if expected_confidence is None or actual_confidence is None:
            return "uncertain"

        # اگر confidence هر کدام پایین باشد،
        # نمی‌توانیم با اطمینان match را تأیید کنیم.
        if (
            expected_confidence < self.medium_confidence_threshold
            or actual_confidence < self.medium_confidence_threshold
        ):
            return "uncertain"

        return "confirmed_match"

    def _match_reason(
        self,
        expected_confidence: float | None,
        actual_confidence: float | None,
    ) -> str:
    
        if (
            expected_confidence is None
            or actual_confidence is None
        ):
            return (
                "Phoneme matched, but recognition "
                "confidence is unavailable."
            )
    
        if (
            expected_confidence
            < self.medium_confidence_threshold
        ):
            return (
                "Phoneme matched, but reference "
                "recognition confidence is low."
            )
    
        if (
            actual_confidence
            < self.medium_confidence_threshold
        ):
            return (
                "Phoneme matched, but user "
                "recognition confidence is low."
            )
    
        return (
            "Reference and user phonemes match "
            "with sufficient recognition confidence."
        )

    # =========================================================
    # Substitution evidence
    # =========================================================

    def _is_likely_substitution_error(
        self,
        expected_confidence: float | None,
        actual_confidence: float | None,
    ) -> bool:

        # If user phoneme confidence is high, the recognizer
        # has stronger evidence that the user actually produced
        # the recognized phoneme.
        if actual_confidence is not None:

            if actual_confidence >= self.high_confidence_threshold:
                return True

            if actual_confidence < self.medium_confidence_threshold:
                return False

        # If reference confidence is very low,
        # the reference recognition itself may be unreliable.
        if expected_confidence is not None:

            if expected_confidence < self.medium_confidence_threshold:
                return False

        # Medium-confidence substitution:
        # mark it as possible rather than confirmed.
        return False

    def _substitution_evidence_status(
        self,
        expected_confidence: float | None,
        actual_confidence: float | None,
    ) -> str:

        if (
            actual_confidence is not None
            and actual_confidence >= self.high_confidence_threshold
        ):

            if (
                expected_confidence is None
                or expected_confidence >= self.medium_confidence_threshold
            ):
                return "possible_error"

        if (
            actual_confidence is not None
            and actual_confidence < self.medium_confidence_threshold
        ):
            return "uncertain"

        return "possible_error"

    def _substitution_confidence_level(
        self,
        expected_confidence: float | None,
        actual_confidence: float | None,
    ) -> str:

        confidences = [
            confidence
            for confidence in (
                expected_confidence,
                actual_confidence,
            )
            if confidence is not None
        ]

        if not confidences:
            return "unknown"

        combined_confidence = min(confidences)

        return self._confidence_level(combined_confidence)

    def _substitution_reason(
        self,
        expected: str | None,
        actual: str | None,
        expected_confidence: float | None,
        actual_confidence: float | None,
    ) -> str:

        if actual_confidence is None:
            return (
                f"Reference phoneme '{expected}' "
                f"and user phoneme '{actual}' differ, "
                f"but user recognition confidence is unavailable."
            )

        if actual_confidence >= self.high_confidence_threshold:

            return (
                f"Reference phoneme '{expected}' "
                f"was recognized as '{actual}' "
                f"with high confidence. "
                f"This is evidence of a possible "
                f"pronunciation substitution."
            )

        if actual_confidence < self.medium_confidence_threshold:

            return (
                f"Reference phoneme '{expected}' "
                f"was recognized as '{actual}', "
                f"but user recognition confidence is low. "
                f"The difference may be a recognition error."
            )

        return (
            f"Reference phoneme '{expected}' "
            f"was recognized as '{actual}' "
            f"with medium confidence. "
            f"Further evidence is needed."
        )

    # =========================================================
    # Summary
    # =========================================================

    def _build_summary(
        self,
        evidence: list[dict],
    ) -> dict:

        confirmed_matches = sum(
            1 for item in evidence if item.get("evidence_status") == "confirmed_match"
        )

        possible_errors = sum(
            1 for item in evidence if item.get("evidence_status") == "possible_error"
        )

        uncertain = sum(
            1 for item in evidence if item.get("evidence_status") == "uncertain"
        )

        likely_errors = sum(1 for item in evidence if item.get("likely_error"))

        return {
            "total": len(evidence),
            "confirmed_matches": (confirmed_matches),
            "possible_errors": (possible_errors),
            "uncertain": uncertain,
            "likely_errors": likely_errors,
        }
