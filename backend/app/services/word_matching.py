import re
from difflib import SequenceMatcher


NORMALIZATION_MAP = {
    # Contractions
    "im": ["i", "am"],
    "i'm": ["i", "am"],

    "ive": ["i", "have"],
    "i've": ["i", "have"],

    "id": ["i", "would"],
    "i'd": ["i", "would"],

    "ill": ["i", "will"],
    "i'll": ["i", "will"],

    "youre": ["you", "are"],
    "you're": ["you", "are"],

    "youve": ["you", "have"],
    "you've": ["you", "have"],

    "youll": ["you", "will"],
    "you'll": ["you", "will"],

    "you'd": ["you", "would"],

    "hes": ["he", "is"],
    "he's": ["he", "is"],

    "shes": ["she", "is"],
    "she's": ["she", "is"],

    "its": ["it", "is"],
    "it's": ["it", "is"],

    "were": ["we", "are"],
    "we're": ["we", "are"],

    "weve": ["we", "have"],
    "we've": ["we", "have"],

    "theyre": ["they", "are"],
    "they're": ["they", "are"],

    "theyve": ["they", "have"],
    "they've": ["they", "have"],

    # Negative contractions
    "dont": ["do", "not"],
    "don't": ["do", "not"],

    "doesnt": ["does", "not"],
    "doesn't": ["does", "not"],

    "didnt": ["did", "not"],
    "didn't": ["did", "not"],

    "cant": ["cannot"],
    "can't": ["cannot"],

    "couldnt": ["could", "not"],
    "couldn't": ["could", "not"],

    "wont": ["will", "not"],
    "won't": ["will", "not"],

    "wouldnt": ["would", "not"],
    "wouldn't": ["would", "not"],

    "shouldnt": ["should", "not"],
    "shouldn't": ["should", "not"],

    "isnt": ["is", "not"],
    "isn't": ["is", "not"],

    "arent": ["are", "not"],
    "aren't": ["are", "not"],

    "wasnt": ["was", "not"],
    "wasn't": ["was", "not"],

    "werent": ["were", "not"],
    "weren't": ["were", "not"],

    # Spoken English
    "gonna": ["going", "to"],
    "wanna": ["want", "to"],
    "gotta": ["got", "to"],
}


def clean_word(word: str) -> str:
    word = word.lower().strip()

    return re.sub(
        r"[^\w']",
        "",
        word,
    )


def tokenize(text: str) -> list[str]:
    return [
        clean_word(word)
        for word in text.split()
        if clean_word(word)
    ]


def normalize_word(word: str) -> list[str]:
    cleaned = clean_word(word)

    return NORMALIZATION_MAP.get(
        cleaned,
        [cleaned],
    )


def normalized_text(words: list[str]) -> list[str]:
    result = []

    for word in words:
        result.extend(
            normalize_word(word)
        )

    return result


def normalized_equal(
    expected: list[str],
    actual: list[str],
) -> bool:

    return (
        normalized_text(expected)
        == normalized_text(actual)
    )


def compare_words(
    expected_text: str,
    transcribed_text: str,
) -> dict:

    expected_words = tokenize(expected_text)
    actual_words = tokenize(transcribed_text)

    matches = []

    i = 0
    j = 0

    correct = 0
    missing = 0
    extra = 0
    replaced = 0

    while (
        i < len(expected_words)
        and j < len(actual_words)
    ):

        expected_word = expected_words[i]
        actual_word = actual_words[j]

        # ==================================================
        # 1. EXACT MATCH
        # ==================================================

        if expected_word == actual_word:

            matches.append({
                "expected": [expected_word],
                "actual": [actual_word],
                "status": "correct",
                "match_type": "exact",
            })

            correct += 1

            i += 1
            j += 1

            continue

        # ==================================================
        # 2. NORMALIZED ONE-TO-ONE
        # ==================================================

        if normalized_equal(
            [expected_word],
            [actual_word],
        ):

            matches.append({
                "expected": [expected_word],
                "actual": [actual_word],
                "status": "correct",
                "match_type": "normalized",
            })

            correct += 1

            i += 1
            j += 1

            continue

        # ==================================================
        # 3. MANY EXPECTED -> ONE ACTUAL
        #
        # I am -> I'm
        # going to -> gonna
        # ==================================================

        found = False

        max_expected_length = min(
            4,
            len(expected_words) - i,
        )

        for length in range(
            2,
            max_expected_length + 1,
        ):

            expected_group = expected_words[
                i:i + length
            ]

            if normalized_equal(
                expected_group,
                [actual_word],
            ):

                matches.append({
                    "expected": expected_group,
                    "actual": [actual_word],
                    "status": "correct",
                    "match_type": "normalized",
                })

                correct += length

                i += length
                j += 1

                found = True

                break

        if found:
            continue

        # ==================================================
        # 4. ONE EXPECTED -> MANY ACTUAL
        #
        # I'm -> I am
        # ==================================================

        found = False

        max_actual_length = min(
            4,
            len(actual_words) - j,
        )

        for length in range(
            2,
            max_actual_length + 1,
        ):

            actual_group = actual_words[
                j:j + length
            ]

            if normalized_equal(
                [expected_word],
                actual_group,
            ):

                matches.append({
                    "expected": [expected_word],
                    "actual": actual_group,
                    "status": "correct",
                    "match_type": "normalized",
                })

                correct += 1

                i += 1
                j += length

                found = True

                break

        if found:
            continue

        # ==================================================
        # 5. LOOKAHEAD - MISSING WORD
        #
        # Expected:
        # a needle
        #
        # Actual:
        # needle
        #
        # Current:
        # a != needle
        #
        # But:
        # next expected == current actual
        #
        # Therefore "a" is missing.
        # ==================================================

        if (
            i + 1 < len(expected_words)
            and expected_words[i + 1]
            == actual_word
        ):

            matches.append({
                "expected": [expected_word],
                "actual": [],
                "status": "missing",
                "match_type": "none",
            })

            missing += 1

            i += 1

            continue

        # ==================================================
        # 6. LOOKAHEAD - EXTRA WORD
        #
        # Expected:
        # needle
        #
        # Actual:
        # very needle
        #
        # Current:
        # needle != very
        #
        # But:
        # current expected == next actual
        #
        # Therefore "very" is extra.
        # ==================================================

        if (
            j + 1 < len(actual_words)
            and expected_word
            == actual_words[j + 1]
        ):

            matches.append({
                "expected": [],
                "actual": [actual_word],
                "status": "extra",
                "match_type": "none",
            })

            extra += 1

            j += 1

            continue

        # ==================================================
        # 7. REPLACED
        # ==================================================

        matches.append({
            "expected": [expected_word],
            "actual": [actual_word],
            "status": "replaced",
            "match_type": "none",
        })

        replaced += 1

        i += 1
        j += 1

    # ======================================================
    # 8. REMAINING EXPECTED = MISSING
    # ======================================================

    while i < len(expected_words):

        matches.append({
            "expected": [expected_words[i]],
            "actual": [],
            "status": "missing",
            "match_type": "none",
        })

        missing += 1

        i += 1

    # ======================================================
    # 9. REMAINING ACTUAL = EXTRA
    # ======================================================

    while j < len(actual_words):

        matches.append({
            "expected": [],
            "actual": [actual_words[j]],
            "status": "extra",
            "match_type": "none",
        })

        extra += 1

        j += 1

    # ======================================================
    # 10. ACCURACY
    # ======================================================

    total_expected = len(expected_words)

    accuracy = (
        correct
        / total_expected
        * 100
        if total_expected > 0
        else 0
    )

    return {
        "expected_text": expected_text,
        "transcribed_text": transcribed_text,

        "matches": matches,

        "statistics": {
            "total_expected": total_expected,
            "correct": correct,
            "missing": missing,
            "extra": extra,
            "replaced": replaced,
        },

        "accuracy": round(
            accuracy,
            1,
        ),
    }


# ==========================================================
# Index-aware alignment
#
# Same alignment algorithm as compare_words(), but tracks
# WORD INDICES instead of word strings. This lets callers
# (e.g. pronunciation analysis) map an aligned word back to
# its original position in a words-with-timestamps list from
# speech-to-text, which compare_words() throws away.
#
# Kept as a separate function (rather than refactoring
# compare_words) to avoid touching the already-relied-upon
# word matching behavior used by the shadowing endpoint.
# ==========================================================

def align_words_with_indices(
    expected_words: list[str],
    actual_words: list[str],
) -> list[dict]:

    alignment = []

    i = 0
    j = 0

    while (
        i < len(expected_words)
        and j < len(actual_words)
    ):

        expected_word = expected_words[i]
        actual_word = actual_words[j]

        # 1. EXACT MATCH
        if expected_word == actual_word:

            alignment.append({
                "expected_indices": [i],
                "actual_indices": [j],
                "status": "correct",
                "match_type": "exact",
            })

            i += 1
            j += 1

            continue

        # 2. NORMALIZED ONE-TO-ONE
        if normalized_equal(
            [expected_word],
            [actual_word],
        ):

            alignment.append({
                "expected_indices": [i],
                "actual_indices": [j],
                "status": "correct",
                "match_type": "normalized",
            })

            i += 1
            j += 1

            continue

        # 3. MANY EXPECTED -> ONE ACTUAL
        found = False

        max_expected_length = min(
            4,
            len(expected_words) - i,
        )

        for length in range(2, max_expected_length + 1):

            expected_group = expected_words[i:i + length]

            if normalized_equal(
                expected_group,
                [actual_word],
            ):

                alignment.append({
                    "expected_indices": list(range(i, i + length)),
                    "actual_indices": [j],
                    "status": "correct",
                    "match_type": "normalized",
                })

                i += length
                j += 1

                found = True

                break

        if found:
            continue

        # 4. ONE EXPECTED -> MANY ACTUAL
        found = False

        max_actual_length = min(
            4,
            len(actual_words) - j,
        )

        for length in range(2, max_actual_length + 1):

            actual_group = actual_words[j:j + length]

            if normalized_equal(
                [expected_word],
                actual_group,
            ):

                alignment.append({
                    "expected_indices": [i],
                    "actual_indices": list(range(j, j + length)),
                    "status": "correct",
                    "match_type": "normalized",
                })

                i += 1
                j += length

                found = True

                break

        if found:
            continue

        # 5. LOOKAHEAD - MISSING WORD
        if (
            i + 1 < len(expected_words)
            and expected_words[i + 1] == actual_word
        ):

            alignment.append({
                "expected_indices": [i],
                "actual_indices": [],
                "status": "missing",
                "match_type": "none",
            })

            i += 1

            continue

        # 6. LOOKAHEAD - EXTRA WORD
        if (
            j + 1 < len(actual_words)
            and expected_word == actual_words[j + 1]
        ):

            alignment.append({
                "expected_indices": [],
                "actual_indices": [j],
                "status": "extra",
                "match_type": "none",
            })

            j += 1

            continue

        # 7. REPLACED
        alignment.append({
            "expected_indices": [i],
            "actual_indices": [j],
            "status": "replaced",
            "match_type": "none",
        })

        i += 1
        j += 1

    # REMAINING EXPECTED = MISSING
    while i < len(expected_words):

        alignment.append({
            "expected_indices": [i],
            "actual_indices": [],
            "status": "missing",
            "match_type": "none",
        })

        i += 1

    # REMAINING ACTUAL = EXTRA
    while j < len(actual_words):

        alignment.append({
            "expected_indices": [],
            "actual_indices": [j],
            "status": "extra",
            "match_type": "none",
        })

        j += 1

    return alignment