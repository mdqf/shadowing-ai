from __future__ import annotations

from dataclasses import dataclass
from typing import Optional


# Small phoneme normalization table. The recognizer already emits
# canonical tokens such as "hh", "eh", "ow"; this is only for
# harmless aliases that can appear across model/tokenizer versions.
ALIASES = {
    "sil": "<blank>",
    "sp": "<blank>",
}


@dataclass(frozen=True)
class AlignmentCell:
    expected_index: Optional[int]
    actual_index: Optional[int]
    operation: str
    cost: float


def normalize_phoneme(phoneme: str) -> str:
    token = phoneme.strip().lower()
    return ALIASES.get(token, token)


def _substitution_cost(expected: str, actual: str) -> float:
    expected = normalize_phoneme(expected)
    actual = normalize_phoneme(actual)

    if expected == actual:
        return 0.0

    # Vowel-vowel and consonant-consonant substitutions are still
    # errors, but slightly cheaper than a cross-class substitution.
    vowels = {
        "aa", "ae", "ah", "ao", "aw", "ay", "eh", "er",
        "ey", "ih", "iy", "ow", "oy", "uh", "uw",
    }

    if (expected in vowels) == (actual in vowels):
        return 0.85

    return 1.0


def align_phonemes(
    expected: list[str],
    actual: list[str],
) -> list[dict]:
    """
    Global Levenshtein/Needleman-Wunsch alignment for phoneme
    sequences.

    Operations:
      match       expected <-> actual
      substitution
      deletion    expected phoneme missing in actual
      insertion   extra actual phoneme

    Unlike positional comparison, this remains stable when the learner
    inserts/deletes a sound or when the two sequences have different
    lengths.
    """

    n = len(expected)
    m = len(actual)

    if n == 0 and m == 0:
        return []

    dp = [[0.0] * (m + 1) for _ in range(n + 1)]
    back: list[list[Optional[str]]] = [
        [None] * (m + 1) for _ in range(n + 1)
    ]

    deletion_cost = 1.0
    insertion_cost = 1.0

    for i in range(1, n + 1):
        dp[i][0] = i * deletion_cost
        back[i][0] = "deletion"

    for j in range(1, m + 1):
        dp[0][j] = j * insertion_cost
        back[0][j] = "insertion"

    priority = {
        "match": 0,
        "substitution": 1,
        "deletion": 2,
        "insertion": 3,
    }

    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sub_op = (
                "match"
                if normalize_phoneme(expected[i - 1])
                == normalize_phoneme(actual[j - 1])
                else "substitution"
            )

            candidates = [
                (
                    dp[i - 1][j - 1] + _substitution_cost(
                        expected[i - 1], actual[j - 1]
                    ),
                    sub_op,
                ),
                (dp[i - 1][j] + deletion_cost, "deletion"),
                (dp[i][j - 1] + insertion_cost, "insertion"),
            ]

            best_cost, best_op = min(
                candidates,
                key=lambda item: (item[0], priority[item[1]]),
            )

            dp[i][j] = best_cost
            back[i][j] = best_op

    cells: list[AlignmentCell] = []
    i = n
    j = m

    while i > 0 or j > 0:
        operation = back[i][j]

        if operation in ("match", "substitution"):
            cells.append(
                AlignmentCell(i - 1, j - 1, operation, dp[i][j])
            )
            i -= 1
            j -= 1
        elif operation == "deletion":
            cells.append(
                AlignmentCell(i - 1, None, operation, dp[i][j])
            )
            i -= 1
        elif operation == "insertion":
            cells.append(
                AlignmentCell(None, j - 1, operation, dp[i][j])
            )
            j -= 1
        else:
            raise RuntimeError("Phoneme alignment backtrace failed.")

    cells.reverse()

    results = []
    for cell in cells:
        result = {
            "expected_index": cell.expected_index,
            "actual_index": cell.actual_index,
            "expected": (
                expected[cell.expected_index]
                if cell.expected_index is not None
                else None
            ),
            "actual": (
                actual[cell.actual_index]
                if cell.actual_index is not None
                else None
            ),
            "status": cell.operation,
        }
        results.append(result)

    return results


def score_alignment(alignment: list[dict], expected_count: int) -> float:
    """
    Sentence-level phoneme score.

    Correct phonemes receive 1.0.
    Substitutions, deletions and insertions reduce the score.
    The denominator includes expected phonemes plus extra sounds,
    so adding many incorrect sounds cannot inflate the score.
    """

    if expected_count == 0:
        return 0.0

    matches = sum(
        1 for item in alignment if item["status"] == "match"
    )
    substitutions = sum(
        1 for item in alignment if item["status"] == "substitution"
    )
    deletions = sum(
        1 for item in alignment if item["status"] == "deletion"
    )
    insertions = sum(
        1 for item in alignment if item["status"] == "insertion"
    )

    # A substitution is one wrong expected phoneme. An insertion is an
    # extra sound and therefore also counts against the final result.
    numerator = matches
    denominator = expected_count + insertions

    # Guard against numerical/pathological cases.
    if denominator <= 0:
        return 0.0

    # Keep substitutions/deletions explicit in the formula. This also
    # makes the returned diagnostics easy to audit.
    _ = substitutions, deletions

    return round(max(0.0, min(100.0, 100.0 * numerator / denominator)), 1)


def attach_timestamps(
    alignment: list[dict],
    expected_timestamps: list[dict | None],
    actual_timestamps: list[dict | None],
) -> list[dict]:
    """Attach available time spans without inventing missing timestamps."""

    output = []

    for item in alignment:
        enriched = dict(item)

        expected_index = item["expected_index"]
        actual_index = item["actual_index"]

        enriched["expected_timestamp"] = (
            expected_timestamps[expected_index]
            if expected_index is not None
            and expected_index < len(expected_timestamps)
            else None
        )

        enriched["actual_timestamp"] = (
            actual_timestamps[actual_index]
            if actual_index is not None
            and actual_index < len(actual_timestamps)
            else None
        )

        output.append(enriched)

    return output
