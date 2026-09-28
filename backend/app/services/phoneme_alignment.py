from __future__ import annotations


class PhonemeAlignmentService:
    """
    Global alignment between reference and user phoneme sequences.

    Supported operations:
    - match
    - substitution
    - deletion
    - insertion

    Confidence values are preserved from the phoneme recognition
    stage so that later stages can distinguish between:
    - a likely pronunciation error
    - a low-confidence recognition
    """

    # =========================================================
    # Initialization
    # =========================================================

    def __init__(
        self,
        substitution_cost: float = 1.0,
        insertion_cost: float = 1.0,
        deletion_cost: float = 1.0,
    ):
        self.substitution_cost = substitution_cost
        self.insertion_cost = insertion_cost
        self.deletion_cost = deletion_cost

    # =========================================================
    # Helpers
    # =========================================================

    @staticmethod
    def _get_confidence(
        phoneme_data: dict | None,
    ) -> float | None:

        if phoneme_data is None:
            return None

        confidence = phoneme_data.get(
            "confidence"
        )

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

    @staticmethod
    def _get_timestamp(
        phoneme_data: dict | None,
    ) -> dict | None:

        if phoneme_data is None:
            return None

        start = phoneme_data.get("start")
        end = phoneme_data.get("end")
        duration = phoneme_data.get("duration")

        if (
            start is None
            or end is None
        ):
            return None

        return {
            "start": start,
            "end": end,
            "duration": duration,
        }

    # =========================================================
    # Main alignment
    # =========================================================

    def align(
        self,
        reference_phonemes: list[dict],
        user_phonemes: list[dict],
    ) -> dict:

        reference_count = len(
            reference_phonemes
        )

        user_count = len(
            user_phonemes
        )

        # -----------------------------------------------------
        # Empty input
        # -----------------------------------------------------

        if (
            reference_count == 0
            and user_count == 0
        ):
            return {
                "alignment": [],
                "distance": 0.0,
                "reference_phoneme_count": 0,
                "user_phoneme_count": 0,
                "matches": 0,
                "substitutions": 0,
                "deletions": 0,
                "insertions": 0,
                "total_operations": 0,
                "accuracy": 1.0,
            }

        # -----------------------------------------------------
        # DP matrix
        # -----------------------------------------------------

        dp = [
            [0.0] * (user_count + 1)
            for _ in range(reference_count + 1)
        ]

        # -----------------------------------------------------
        # Initialize first column
        # -----------------------------------------------------

        for i in range(
            1,
            reference_count + 1,
        ):
            dp[i][0] = (
                i * self.deletion_cost
            )

        # -----------------------------------------------------
        # Initialize first row
        # -----------------------------------------------------

        for j in range(
            1,
            user_count + 1,
        ):
            dp[0][j] = (
                j * self.insertion_cost
            )

        # -----------------------------------------------------
        # Dynamic programming
        # -----------------------------------------------------

        for i in range(
            1,
            reference_count + 1,
        ):

            reference_phoneme = (
                reference_phonemes[i - 1]
                .get("phoneme")
            )

            for j in range(
                1,
                user_count + 1,
            ):

                user_phoneme = (
                    user_phonemes[j - 1]
                    .get("phoneme")
                )

                # Match
                if (
                    reference_phoneme
                    == user_phoneme
                ):
                    substitution_cost = 0.0
                else:
                    substitution_cost = (
                        self.substitution_cost
                    )

                match_or_substitution = (
                    dp[i - 1][j - 1]
                    + substitution_cost
                )

                deletion = (
                    dp[i - 1][j]
                    + self.deletion_cost
                )

                insertion = (
                    dp[i][j - 1]
                    + self.insertion_cost
                )

                dp[i][j] = min(
                    match_or_substitution,
                    deletion,
                    insertion,
                )

        # -----------------------------------------------------
        # Backtracking
        # -----------------------------------------------------

        alignment = []

        i = reference_count
        j = user_count

        while (
            i > 0
            or j > 0
        ):

            # -------------------------------------------------
            # Match / substitution
            # -------------------------------------------------

            if (
                i > 0
                and j > 0
            ):

                reference_item = (
                    reference_phonemes[i - 1]
                )

                user_item = (
                    user_phonemes[j - 1]
                )

                reference_phoneme = (
                    reference_item.get(
                        "phoneme"
                    )
                )

                user_phoneme = (
                    user_item.get(
                        "phoneme"
                    )
                )

                if (
                    reference_phoneme
                    == user_phoneme
                ):
                    operation_cost = 0.0
                    status = "match"
                else:
                    operation_cost = (
                        self.substitution_cost
                    )
                    status = "substitution"

                expected_score = (
                    dp[i - 1][j - 1]
                    + operation_cost
                )

                if abs(
                    dp[i][j]
                    - expected_score
                ) < 1e-9:

                    alignment.append(
                        self._build_alignment_item(
                            reference_item=reference_item,
                            user_item=user_item,
                            status=status,
                        )
                    )

                    i -= 1
                    j -= 1

                    continue

            # -------------------------------------------------
            # Deletion
            # -------------------------------------------------

            if i > 0:

                expected_score = (
                    dp[i - 1][j]
                    + self.deletion_cost
                )

                if abs(
                    dp[i][j]
                    - expected_score
                ) < 1e-9:

                    reference_item = (
                        reference_phonemes[i - 1]
                    )

                    alignment.append(
                        self._build_alignment_item(
                            reference_item=reference_item,
                            user_item=None,
                            status="deletion",
                        )
                    )

                    i -= 1

                    continue

            # -------------------------------------------------
            # Insertion
            # -------------------------------------------------

            if j > 0:

                user_item = (
                    user_phonemes[j - 1]
                )

                alignment.append(
                    self._build_alignment_item(
                        reference_item=None,
                        user_item=user_item,
                        status="insertion",
                    )
                )

                j -= 1

                continue

        # Backtracking starts from the end.
        alignment.reverse()

        # -----------------------------------------------------
        # Statistics
        # -----------------------------------------------------

        matches = sum(
            1
            for item in alignment
            if item["status"] == "match"
        )

        substitutions = sum(
            1
            for item in alignment
            if item["status"] == "substitution"
        )

        deletions = sum(
            1
            for item in alignment
            if item["status"] == "deletion"
        )

        insertions = sum(
            1
            for item in alignment
            if item["status"] == "insertion"
        )

        total_operations = len(
            alignment
        )

        distance = dp[
            reference_count
        ][
            user_count
        ]

        # -----------------------------------------------------
        # Accuracy
        # -----------------------------------------------------

        if reference_count == 0:

            accuracy = (
                1.0
                if user_count == 0
                else 0.0
            )

        else:

            accuracy = (
                matches
                / reference_count
            )

        return {
            "alignment": alignment,
            "distance": round(
                distance,
                3,
            ),
            "reference_phoneme_count": (
                reference_count
            ),
            "user_phoneme_count": (
                user_count
            ),
            "matches": matches,
            "substitutions": substitutions,
            "deletions": deletions,
            "insertions": insertions,
            "total_operations": total_operations,
            "accuracy": round(
                accuracy,
                3,
            ),
        }

    # =========================================================
    # Build alignment item
    # =========================================================

    def _build_alignment_item(
        self,
        reference_item: dict | None,
        user_item: dict | None,
        status: str,
    ) -> dict:

        # -----------------------------------------------------
        # Reference information
        # -----------------------------------------------------

        expected = None
        expected_timestamp = None
        expected_confidence = None

        if reference_item is not None:

            expected = reference_item.get(
                "phoneme"
            )

            expected_timestamp = (
                self._get_timestamp(
                    reference_item
                )
            )

            expected_confidence = (
                self._get_confidence(
                    reference_item
                )
            )

        # -----------------------------------------------------
        # User information
        # -----------------------------------------------------

        actual = None
        actual_timestamp = None
        actual_confidence = None

        if user_item is not None:

            actual = user_item.get(
                "phoneme"
            )

            actual_timestamp = (
                self._get_timestamp(
                    user_item
                )
            )

            actual_confidence = (
                self._get_confidence(
                    user_item
                )
            )

        # -----------------------------------------------------
        # Result
        # -----------------------------------------------------

        return {
            "expected": expected,
            "actual": actual,
            "status": status,
            "expected_timestamp": (
                expected_timestamp
            ),
            "actual_timestamp": (
                actual_timestamp
            ),
            "expected_confidence": (
                expected_confidence
            ),
            "actual_confidence": (
                actual_confidence
            ),
        }