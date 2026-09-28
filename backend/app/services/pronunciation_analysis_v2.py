from typing import Any, Dict, List, Optional

from app.services.phonetic_similarity import PhoneticSimilarityService
from app.services.pronunciation_severity import PronunciationSeverityService
from app.services.word_phoneme_mapping import WordPhonemeMappingService
from app.services.l1_feedback import L1FeedbackService


class PronunciationAnalysisV2:
    """
    Unified pronunciation analysis layer.

    Combines:
    - phoneme alignment
    - recognition confidence
    - pronunciation evidence
    - phonetic similarity
    - pronunciation severity
    - word-level grouping (optional, requires expected_text)
    - L1-specific feedback tips (optional, currently Persian only)

    This service does NOT perform phoneme recognition or alignment itself.
    It only interprets the already-aligned phoneme results.
    """

    def __init__(self):
        self.similarity_service = PhoneticSimilarityService()
        self.severity_service = PronunciationSeverityService()
        self.word_mapping_service = WordPhonemeMappingService()
        self.l1_feedback_service = L1FeedbackService()

    def analyze(
        self,
        alignment_result: Dict[str, Any],
        evidence_result: Dict[str, Any],
        expected_text: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Combine alignment + evidence + phonetic similarity + severity.

        If expected_text is provided, also attaches a "word_breakdown":
        the same phoneme items grouped by the word they belong to.
        """

        alignment_items = alignment_result.get("alignment", [])
        evidence_items = evidence_result.get("evidence", [])
        if not evidence_items:
            raise ValueError(
                "Pronunciation evidence is empty or missing."
            )

        analyzed_items: List[Dict[str, Any]] = []

        for index, alignment_item in enumerate(alignment_items):
            evidence_item = (
                evidence_items[index]
                if index < len(evidence_items)
                else {}
            )

            analyzed_item = self._analyze_item(
                alignment_item=alignment_item,
                evidence_item=evidence_item,
            )

            analyzed_items.append(analyzed_item)

        summary = self._build_summary(analyzed_items)

        word_breakdown: List[Dict[str, Any]] = []
        word_index_map: List[Optional[int]] = [None] * len(analyzed_items)

        if expected_text:
            try:
                word_index_map = (
                    self.word_mapping_service.get_word_index_mapping(
                        expected_text=expected_text,
                        items=analyzed_items,
                    )
                )

                # Positional L1 patterns (e.g. /ŋ/+/g/, word-initial
                # /s/-cluster vowel epenthesis) need word-boundary
                # context, so they run after alignment but before
                # word_breakdown is built — that way each word's
                # issue list already carries the tip.
                positional_tips = (
                    self.l1_feedback_service.get_positional_tips(
                        items=analyzed_items,
                        word_index_map=word_index_map,
                    )
                )

                for index, tip in enumerate(positional_tips):
                    if tip and not analyzed_items[index].get("l1_tip"):
                        analyzed_items[index]["l1_tip"] = tip

                word_breakdown = self.word_mapping_service.map_words(
                    expected_text=expected_text,
                    items=analyzed_items,
                )
            except Exception:
                # Word-level grouping is a best-effort convenience
                # layer. If it fails for any reason, the raw phoneme
                # analysis above must still be returned unaffected.
                word_breakdown = []
                word_index_map = [None] * len(analyzed_items)

        return {
            "items": analyzed_items,
            "summary": summary,
            "word_breakdown": word_breakdown,
            "word_index_map": word_index_map,
        }

    def _analyze_item(
        self,
        alignment_item: Dict[str, Any],
        evidence_item: Dict[str, Any],
    ) -> Dict[str, Any]:

        expected = alignment_item.get("expected")
        actual = alignment_item.get("actual")
        status = alignment_item.get("status")

        expected_confidence = self._get_confidence(
            alignment_item,
            "expected_confidence",
        )

        actual_confidence = self._get_confidence(
            alignment_item,
            "actual_confidence",
        )

        evidence_status = evidence_item.get(
            "evidence_status",
            "unknown",
        )

        likely_error = evidence_item.get(
            "likely_error",
            False,
        )

        # ---------------------------------------------------------
        # MATCH
        # ---------------------------------------------------------

        if status == "match" and expected and actual:
            similarity_result = self.similarity_service.compare(
                expected=expected,
                actual=actual,
            )

        # ---------------------------------------------------------
        # SUBSTITUTION
        # ---------------------------------------------------------

        elif status == "substitution" and expected and actual:
            similarity_result = self.similarity_service.compare(
                expected=expected,
                actual=actual,
            )

        # ---------------------------------------------------------
        # DELETION
        # ---------------------------------------------------------

        elif status == "deletion":
            similarity_result = {
                "expected": expected,
                "actual": None,
                "phonetic_similarity": 0.0,
                "phonetic_distance": 1.0,
                "error_type": "deletion",
            }

        # ---------------------------------------------------------
        # INSERTION
        # ---------------------------------------------------------

        elif status == "insertion":
            similarity_result = {
                "expected": None,
                "actual": actual,
                "phonetic_similarity": 0.0,
                "phonetic_distance": 1.0,
                "error_type": "insertion",
            }

        else:
            similarity_result = {
                "expected": expected,
                "actual": actual,
                "phonetic_similarity": 0.0,
                "phonetic_distance": 0.0,
                "error_type": None,
            }

        # ---------------------------------------------------------
        # PHONEME SCORE
        # ---------------------------------------------------------

        if status == "match":
            phoneme_score = 100.0

        elif status == "substitution":

            # phonetic_similarity can be None when either phoneme
            # is missing from the PhoneticSimilarityService dictionary
            # (unknown/unsupported phoneme symbol). We must not crash
            # the whole analysis for that — fall back to 0.0 and let
            # evidence/severity reflect the uncertainty instead.
            raw_similarity = similarity_result["phonetic_similarity"]

            phoneme_score = (
                raw_similarity * 100.0
                if raw_similarity is not None
                else 0.0
            )

        elif status in ("deletion", "insertion"):
            phoneme_score = 0.0

        else:
            phoneme_score = 0.0

        # ---------------------------------------------------------
        # SEVERITY
        # ---------------------------------------------------------

        severity_result = self.severity_service.classify(
            status=status,
            phonetic_similarity=similarity_result["phonetic_similarity"],
            expected_confidence=expected_confidence,
            actual_confidence=actual_confidence,
            evidence_status=evidence_status,
            likely_error=likely_error,
        )

        # ---------------------------------------------------------
        # MODEL SELF-FLAGGED ERROR (metadata only, does NOT affect
        # scoring/evidence). The slplab L2-English phoneme model tags
        # a phoneme with '_err' when its own training data (Korean L1
        # speakers) considers that segment a likely mispronunciation.
        # We surface this as data for now — it is not yet validated
        # for other L1 backgrounds (e.g. Persian), so it must not
        # silently influence the score.
        # ---------------------------------------------------------

        model_flagged_expected = bool(
            expected and expected.endswith("_err")
        )
        model_flagged_actual = bool(
            actual and actual.endswith("_err")
        )

        # ---------------------------------------------------------
        # L1-SPECIFIC FEEDBACK TIP (Persian only, for now)
        # ---------------------------------------------------------

        l1_tip = self.l1_feedback_service.get_tip(
            expected=expected,
            actual=actual,
            status=status,
        )

        # ---------------------------------------------------------
        # FINAL ITEM
        # ---------------------------------------------------------

        result = dict(alignment_item)

        result.update(
            {
                "phoneme_score": round(
                    phoneme_score,
                    1,
                ),
                "evidence_status": evidence_status,
                "confidence_level": evidence_item.get(
                    "confidence_level"
                ),
                "likely_error": likely_error,
                "evidence_reason": evidence_item.get(
                    "reason"
                ),
                "l1_tip": l1_tip,

                "phonetic_similarity": similarity_result[
                    "phonetic_similarity"
                ],
                "phonetic_distance": similarity_result[
                    "phonetic_distance"
                ],
                "error_type": similarity_result[
                    "error_type"
                ],

                "severity": severity_result[
                    "severity"
                ],
                "severity_score": severity_result[
                    "severity_score"
                ],
                "severity_reason": severity_result[
                    "severity_reason"
                ],

                "model_flagged_expected": model_flagged_expected,
                "model_flagged_actual": model_flagged_actual,
            }
        )

        return result

    @staticmethod
    def _get_confidence(
        item: Dict[str, Any],
        key: str,
    ) -> float:

        value = item.get(key)

        if value is None:
            return 0.0

        try:
            return float(value)
        except (TypeError, ValueError):
            return 0.0

    @staticmethod
    def _build_summary(
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:

        total = len(items)

        matches = sum(
            1
            for item in items
            if item.get("status") == "match"
        )

        substitutions = sum(
            1
            for item in items
            if item.get("status") == "substitution"
        )

        deletions = sum(
            1
            for item in items
            if item.get("status") == "deletion"
        )

        insertions = sum(
            1
            for item in items
            if item.get("status") == "insertion"
        )

        phoneme_scores = [
            float(item.get("phoneme_score", 0.0))
            for item in items
        ]

        pronunciation_score = (
            sum(phoneme_scores) / len(phoneme_scores)
            if phoneme_scores
            else 0.0
        )

        phoneme_accuracy = (
            (matches / total) * 100.0
            if total
            else 0.0
        )

        confirmed_matches = sum(
            1
            for item in items
            if item.get("evidence_status")
            == "confirmed_match"
        )

        possible_errors = sum(
            1
            for item in items
            if item.get("evidence_status")
            == "possible_error"
        )

        uncertain = sum(
            1
            for item in items
            if item.get("evidence_status")
            == "uncertain"
        )

        likely_errors = sum(
            1
            for item in items
            if item.get("likely_error") is True
        )

        severe = sum(
            1
            for item in items
            if item.get("severity") == "severe"
        )

        moderate = sum(
            1
            for item in items
            if item.get("severity") == "moderate"
        )

        mild = sum(
            1
            for item in items
            if item.get("severity") == "mild"
        )

        severity_scores = [
            float(item.get("severity_score", 0.0))
            for item in items
            if item.get("severity_score") is not None
        ]

        average_severity = (
            sum(severity_scores) / len(severity_scores)
            if severity_scores
            else 0.0
        )

        model_flagged_actual_count = sum(
            1
            for item in items
            if item.get("model_flagged_actual") is True
        )

        return {
            "total": total,

            "matches": matches,
            "substitutions": substitutions,
            "deletions": deletions,
            "insertions": insertions,

            "model_flagged_actual_count": model_flagged_actual_count,

            "phoneme_accuracy": round(
                phoneme_accuracy,
                1,
            ),

            "pronunciation_score": round(
                pronunciation_score,
                1,
            ),

            "confirmed_matches": confirmed_matches,
            "possible_errors": possible_errors,
            "uncertain": uncertain,
            "likely_errors": likely_errors,

            "mild": mild,
            "moderate": moderate,
            "severe": severe,

            "average_severity_score": round(
                average_severity,
                2,
            ),
        }