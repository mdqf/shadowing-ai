from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class PhonemeFeatures:
    """
    Articulatory / phonetic features used to compare two phonemes.
    """

    phoneme_type: str

    # Consonant features
    voiced: Optional[bool] = None
    place: Optional[str] = None
    manner: Optional[str] = None

    # Vowel features
    vowel_height: Optional[str] = None
    vowel_backness: Optional[str] = None
    roundedness: Optional[bool] = None


class PhoneticSimilarityService:
    """
    Calculates phonetic similarity between two ARPAbet-style phonemes.

    The service is intentionally independent from phoneme recognition
    and phoneme alignment.
    """

    def __init__(self) -> None:
        self.phoneme_features: Dict[str, PhonemeFeatures] = (
            self._build_phoneme_features()
        )

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def compare(
        self,
        expected: str,
        actual: str,
    ) -> dict:
        """
        Compare two phonemes and return similarity information.
        """

        expected = expected.lower().strip()
        actual = actual.lower().strip()

        # The slplab L2-English phoneme model tags a phoneme with an
        # '_err' suffix (e.g. 'd_err') when its own training data marks
        # that segment as a likely mispronunciation. This is a *flag*,
        # not a different phoneme — strip it before looking the phoneme
        # up in the articulatory-features dictionary, so we still get a
        # real similarity score instead of "unknown".
        expected_base = (
            expected[: -len("_err")]
            if expected.endswith("_err")
            else expected
        )
        actual_base = (
            actual[: -len("_err")]
            if actual.endswith("_err")
            else actual
        )

        if expected_base not in self.phoneme_features:
            return self._unknown_result(
                expected=expected,
                actual=actual,
                reason=f"Unknown expected phoneme: '{expected}'",
            )

        if actual_base not in self.phoneme_features:
            return self._unknown_result(
                expected=expected,
                actual=actual,
                reason=f"Unknown actual phoneme: '{actual}'",
            )

        if expected_base == actual_base:
            return {
                "expected": expected,
                "actual": actual,
                "phonetic_similarity": 1.0,
                "phonetic_distance": 0.0,
                "error_type": None,
            }

        expected_features = self.phoneme_features[expected_base]
        actual_features = self.phoneme_features[actual_base]

        similarity = self._calculate_similarity(
            expected_features,
            actual_features,
        )

        distance = round(1.0 - similarity, 4)

        error_type = self._classify_error(
            expected_features,
            actual_features,
        )

        return {
            "expected": expected,
            "actual": actual,
            "phonetic_similarity": round(similarity, 4),
            "phonetic_distance": distance,
            "error_type": error_type,
        }

    # ------------------------------------------------------------------
    # Similarity calculation
    # ------------------------------------------------------------------

    def _calculate_similarity(
        self,
        expected: PhonemeFeatures,
        actual: PhonemeFeatures,
    ) -> float:
        """
        Calculate similarity using articulatory features.

        The weighting is intentionally simple at this stage.
        We can calibrate it later using real learner data.
        """

        if expected.phoneme_type != actual.phoneme_type:
            return 0.10

        if expected.phoneme_type == "vowel":
            return self._vowel_similarity(
                expected,
                actual,
            )

        if expected.phoneme_type == "consonant":
            return self._consonant_similarity(
                expected,
                actual,
            )

        return 0.0

    def _vowel_similarity(
        self,
        expected: PhonemeFeatures,
        actual: PhonemeFeatures,
    ) -> float:

        score = 0.0
        total_weight = 0.0

        # Height
        if (
            expected.vowel_height is not None
            and actual.vowel_height is not None
        ):
            score += (
                self._categorical_similarity(
                    expected.vowel_height,
                    actual.vowel_height,
                )
                * 0.35
            )
            total_weight += 0.35

        # Backness
        if (
            expected.vowel_backness is not None
            and actual.vowel_backness is not None
        ):
            score += (
                self._categorical_similarity(
                    expected.vowel_backness,
                    actual.vowel_backness,
                )
                * 0.35
            )
            total_weight += 0.35

        # Roundedness
        if (
            expected.roundedness is not None
            and actual.roundedness is not None
        ):
            score += (
                1.0
                if expected.roundedness == actual.roundedness
                else 0.0
            ) * 0.30

            total_weight += 0.30

        if total_weight == 0:
            return 0.0

        return score / total_weight

    def _consonant_similarity(
        self,
        expected: PhonemeFeatures,
        actual: PhonemeFeatures,
    ) -> float:

        score = 0.0
        total_weight = 0.0

        # Manner
        if (
            expected.manner is not None
            and actual.manner is not None
        ):
            score += (
                self._categorical_similarity(
                    expected.manner,
                    actual.manner,
                )
                * 0.40
            )
            total_weight += 0.40

        # Place
        if (
            expected.place is not None
            and actual.place is not None
        ):
            score += (
                self._categorical_similarity(
                    expected.place,
                    actual.place,
                )
                * 0.35
            )
            total_weight += 0.35

        # Voicing
        if (
            expected.voiced is not None
            and actual.voiced is not None
        ):
            score += (
                1.0
                if expected.voiced == actual.voiced
                else 0.0
            ) * 0.25

            total_weight += 0.25

        if total_weight == 0:
            return 0.0

        return score / total_weight

    # ------------------------------------------------------------------
    # Error classification
    # ------------------------------------------------------------------

    def _classify_error(
        self,
        expected: PhonemeFeatures,
        actual: PhonemeFeatures,
    ) -> str:

        if (
            expected.phoneme_type == "vowel"
            and actual.phoneme_type == "vowel"
        ):
            return "vowel_substitution"

        if (
            expected.phoneme_type == "consonant"
            and actual.phoneme_type == "consonant"
        ):
            if expected.manner != actual.manner:
                return "consonant_manner_substitution"

            if expected.place != actual.place:
                return "consonant_place_substitution"

            if expected.voiced != actual.voiced:
                return "voicing_substitution"

            return "consonant_substitution"

        return "cross_category_substitution"

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _categorical_similarity(
        expected: str,
        actual: str,
    ) -> float:

        if expected == actual:
            return 1.0

        groups = [
            {"close", "near_close", "mid"},
            {"mid", "near_open", "open"},
            {"front", "central"},
            {"central", "back"},
            {"bilabial", "labiodental"},
            {"dental", "alveolar"},
            {"alveolar", "postalveolar"},
            {"stop", "affricate"},
            {"fricative", "approximant"},
            {"nasal", "approximant"},
        ]

        for group in groups:
            if expected in group and actual in group:
                return 0.5

        return 0.0

    @staticmethod
    def _unknown_result(
        expected: str,
        actual: str,
        reason: str,
    ) -> dict:

        return {
            "expected": expected,
            "actual": actual,
            "phonetic_similarity": None,
            "phonetic_distance": None,
            "error_type": "unknown",
            "reason": reason,
        }

    # ------------------------------------------------------------------
    # Phoneme feature dictionary
    # ------------------------------------------------------------------

    @staticmethod
    def _build_phoneme_features() -> Dict[str, PhonemeFeatures]:

        return {

            # ==========================================================
            # VOWELS
            # ==========================================================

            "iy": PhonemeFeatures(
                phoneme_type="vowel",
                vowel_height="close",
                vowel_backness="front",
                roundedness=False,
            ),

            "ih": PhonemeFeatures(
                phoneme_type="vowel",
                vowel_height="near_close",
                vowel_backness="front",
                roundedness=False,
            ),

            "ey": PhonemeFeatures(
                phoneme_type="vowel",
                vowel_height="mid",
                vowel_backness="front",
                roundedness=False,
            ),

            "eh": PhonemeFeatures(
                phoneme_type="vowel",
                vowel_height="mid",
                vowel_backness="front",
                roundedness=False,
            ),

            "ae": PhonemeFeatures(
                phoneme_type="vowel",
                vowel_height="near_open",
                vowel_backness="front",
                roundedness=False,
            ),

            "aa": PhonemeFeatures(
                phoneme_type="vowel",
                vowel_height="open",
                vowel_backness="back",
                roundedness=False,
            ),

            "ao": PhonemeFeatures(
                phoneme_type="vowel",
                vowel_height="open",
                vowel_backness="back",
                roundedness=True,
            ),

            "ah": PhonemeFeatures(
                phoneme_type="vowel",
                vowel_height="open",
                vowel_backness="central",
                roundedness=False,
            ),

            "er": PhonemeFeatures(
                phoneme_type="vowel",
                vowel_height="mid",
                vowel_backness="central",
                roundedness=False,
            ),

            "ax": PhonemeFeatures(
                phoneme_type="vowel",
                vowel_height="mid",
                vowel_backness="central",
                roundedness=False,
            ),

            "uh": PhonemeFeatures(
                phoneme_type="vowel",
                vowel_height="near_close",
                vowel_backness="back",
                roundedness=True,
            ),

            "uw": PhonemeFeatures(
                phoneme_type="vowel",
                vowel_height="close",
                vowel_backness="back",
                roundedness=True,
            ),

            "ow": PhonemeFeatures(
                phoneme_type="vowel",
                vowel_height="mid",
                vowel_backness="back",
                roundedness=True,
            ),

            "aw": PhonemeFeatures(
                phoneme_type="vowel",
                vowel_height="open",
                vowel_backness="central",
                roundedness=False,
            ),

            "oy": PhonemeFeatures(
                phoneme_type="vowel",
                vowel_height="mid",
                vowel_backness="back",
                roundedness=True,
            ),

            "ay": PhonemeFeatures(
                phoneme_type="vowel",
                vowel_height="open",
                vowel_backness="front",
                roundedness=False,
            ),

            # ==========================================================
            # CONSONANTS
            # ==========================================================

            "p": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=False,
                place="bilabial",
                manner="stop",
            ),

            "b": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=True,
                place="bilabial",
                manner="stop",
            ),

            "t": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=False,
                place="alveolar",
                manner="stop",
            ),

            "d": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=True,
                place="alveolar",
                manner="stop",
            ),

            "k": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=False,
                place="velar",
                manner="stop",
            ),

            "g": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=True,
                place="velar",
                manner="stop",
            ),

            "ch": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=False,
                place="postalveolar",
                manner="affricate",
            ),

            "jh": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=True,
                place="postalveolar",
                manner="affricate",
            ),

            "f": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=False,
                place="labiodental",
                manner="fricative",
            ),

            "v": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=True,
                place="labiodental",
                manner="fricative",
            ),

            "th": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=False,
                place="dental",
                manner="fricative",
            ),

            "dh": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=True,
                place="dental",
                manner="fricative",
            ),

            "s": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=False,
                place="alveolar",
                manner="fricative",
            ),

            "z": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=True,
                place="alveolar",
                manner="fricative",
            ),

            "sh": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=False,
                place="postalveolar",
                manner="fricative",
            ),

            "zh": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=True,
                place="postalveolar",
                manner="fricative",
            ),

            "hh": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=False,
                place="glottal",
                manner="fricative",
            ),

            "m": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=True,
                place="bilabial",
                manner="nasal",
            ),

            "n": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=True,
                place="alveolar",
                manner="nasal",
            ),

            "ng": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=True,
                place="velar",
                manner="nasal",
            ),

            "l": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=True,
                place="alveolar",
                manner="approximant",
            ),

            "r": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=True,
                place="postalveolar",
                manner="approximant",
            ),

            "y": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=True,
                place="palatal",
                manner="approximant",
            ),

            "w": PhonemeFeatures(
                phoneme_type="consonant",
                voiced=True,
                place="labial-velar",
                manner="approximant",
            ),
        }