import re
from typing import Any, Dict, List, Optional, Tuple

import cmudict


class WordPhonemeMappingService:
    """
    Groups phoneme-level pronunciation_analysis_v2 items by the word
    they belong to, so the UI can show "the word 'terrified' had a
    pronunciation issue" instead of only a flat phoneme list.

    How it works:

    1. Split expected_text into words, look up each word's canonical
       pronunciation in cmudict (a standard offline CMU pronouncing
       dictionary), and strip stress digits (e.g. 'EH1' -> 'eh').

    2. The phoneme_analysis_v2 items' "expected" field is NOT the
       canonical dictionary pronunciation — it is whatever the phoneme
       recognition model actually heard in the reference (actor)
       audio, which can be noisy (extra/missing phonemes, model quirks
       like '_err' tags). So we cannot just consume N canonical
       phonemes per word in a fixed-count way; a single early mismatch
       would cascade and misassign every following word.

    3. Instead we run a standard global sequence alignment (Needleman
       -Wunsch style, same idea used elsewhere in this project for
       phoneme alignment) between the canonical phoneme sequence and
       the observed reference-recognized phoneme sequence. This finds
       the best-effort correspondence even when the two sequences
       don't match exactly, and is robust to occasional recognition
       noise.

    4. Every phoneme item is then attributed to a word index based on
       this alignment. Insertions (phonemes the user added with no
       reference counterpart at all) are attached to whichever word
       they fall closest to in time.
    """

    def __init__(self) -> None:
        self._cmu_dict = cmudict.dict()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_word_index_mapping(
        self,
        expected_text: str,
        items: List[Dict[str, Any]],
    ) -> List[Optional[int]]:
        """
        Returns, for each item in `items`, the index of the word
        (into re.findall(...) over expected_text) it was attributed
        to, or None if it couldn't be attributed to any word.

        This is the reusable building block behind map_words() — any
        other service that needs to know "which word does this
        phoneme belong to" (e.g. stress/prosody scoring) should call
        this directly instead of re-deriving alignment on its own.
        """

        words = self._extract_words(expected_text)

        if not words or not items:
            return [None] * len(items)

        canonical_seq, _word_has_dict_entry = self._build_canonical_sequence(
            words
        )

        observed_seq = self._build_observed_sequence(items)

        return self._align_and_attribute(
            canonical_seq=canonical_seq,
            observed_seq=observed_seq,
            item_count=len(items),
        )

    def map_words(
        self,
        expected_text: str,
        items: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:

        breakdown, _mapping = self.map_words_with_index(
            expected_text=expected_text,
            items=items,
        )

        return breakdown

    def map_words_with_index(
        self,
        expected_text: str,
        items: List[Dict[str, Any]],
    ) -> Tuple[List[Dict[str, Any]], List[Optional[int]]]:
        """
        Same as map_words(), but also returns the raw item -> word
        index mapping, so callers that need both (e.g. main.py wiring
        word_breakdown and stress analysis from the same request) only
        pay the alignment cost once.
        """

        words = self._extract_words(expected_text)

        if not words or not items:
            return [], [None] * len(items)

        canonical_seq, word_has_dict_entry = self._build_canonical_sequence(
            words
        )

        observed_seq = self._build_observed_sequence(items)

        item_to_word_index = self._align_and_attribute(
            canonical_seq=canonical_seq,
            observed_seq=observed_seq,
            item_count=len(items),
        )

        breakdown = self._build_word_breakdown(
            words=words,
            items=items,
            item_to_word_index=item_to_word_index,
            word_has_dict_entry=word_has_dict_entry,
        )

        return breakdown, item_to_word_index

    # ------------------------------------------------------------------
    # Step 1: words + canonical phonemes
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_words(expected_text: str) -> List[str]:
        return re.findall(r"[A-Za-z']+", expected_text or "")

    def _canonical_phonemes(self, word: str) -> Optional[List[str]]:

        clean = word.strip("'").lower()

        entries = self._cmu_dict.get(clean)

        if not entries:
            return None

        # cmudict may list multiple pronunciation variants
        # (e.g. "the" -> DH AH0 / DH AH1 / DH IY0). We use the
        # first (most common) variant.
        raw_phonemes = entries[0]

        return [
            re.sub(r"[0-9]", "", p).lower()
            for p in raw_phonemes
        ]

    def _build_canonical_sequence(
        self,
        words: List[str],
    ) -> Tuple[List[Tuple[int, str]], List[bool]]:

        canonical_seq: List[Tuple[int, str]] = []
        word_has_dict_entry: List[bool] = []

        for word_index, word in enumerate(words):

            phonemes = self._canonical_phonemes(word)

            word_has_dict_entry.append(phonemes is not None)

            for phoneme in (phonemes or []):
                canonical_seq.append((word_index, phoneme))

        return canonical_seq, word_has_dict_entry

    # ------------------------------------------------------------------
    # Step 2: observed reference-recognized phoneme sequence
    # ------------------------------------------------------------------

    @staticmethod
    def _base_phoneme(phoneme: Optional[str]) -> Optional[str]:

        if not phoneme:
            return None

        return (
            phoneme[: -len("_err")]
            if phoneme.endswith("_err")
            else phoneme
        )

    def _build_observed_sequence(
        self,
        items: List[Dict[str, Any]],
    ) -> List[Tuple[int, str]]:

        observed_seq: List[Tuple[int, str]] = []

        for item_index, item in enumerate(items):

            base = self._base_phoneme(item.get("expected"))

            # Only items that actually have a reference phoneme
            # (match / substitution / deletion) participate in the
            # word-boundary alignment. Insertions (expected is None)
            # are attached separately afterwards.
            if base:
                observed_seq.append((item_index, base))

        return observed_seq

    # ------------------------------------------------------------------
    # Step 3: sequence alignment (Needleman-Wunsch, unit costs)
    # ------------------------------------------------------------------

    @staticmethod
    def _align_sequences(
        seq_a: List[str],
        seq_b: List[str],
    ) -> List[Tuple[Optional[int], Optional[int]]]:
        """
        Global alignment between seq_a and seq_b using unit match/
        mismatch/gap costs. Returns a list of (index_in_a, index_in_b)
        pairs, using None for a gap on either side.
        """

        n, m = len(seq_a), len(seq_b)

        # dp[i][j] = min edit cost aligning seq_a[:i] with seq_b[:j]
        dp = [[0] * (m + 1) for _ in range(n + 1)]

        for i in range(1, n + 1):
            dp[i][0] = i

        for j in range(1, m + 1):
            dp[0][j] = j

        for i in range(1, n + 1):
            for j in range(1, m + 1):

                match_cost = 0 if seq_a[i - 1] == seq_b[j - 1] else 1

                dp[i][j] = min(
                    dp[i - 1][j - 1] + match_cost,
                    dp[i - 1][j] + 1,
                    dp[i][j - 1] + 1,
                )

        # Backtrace
        pairs: List[Tuple[Optional[int], Optional[int]]] = []
        i, j = n, m

        while i > 0 or j > 0:

            if (
                i > 0
                and j > 0
                and dp[i][j] == dp[i - 1][j - 1]
                + (0 if seq_a[i - 1] == seq_b[j - 1] else 1)
            ):
                pairs.append((i - 1, j - 1))
                i -= 1
                j -= 1

            elif i > 0 and dp[i][j] == dp[i - 1][j] + 1:
                pairs.append((i - 1, None))
                i -= 1

            else:
                pairs.append((None, j - 1))
                j -= 1

        pairs.reverse()

        return pairs

    def _align_and_attribute(
        self,
        canonical_seq: List[Tuple[int, str]],
        observed_seq: List[Tuple[int, str]],
        item_count: int,
    ) -> List[Optional[int]]:

        item_to_word_index: List[Optional[int]] = [None] * item_count

        if not canonical_seq or not observed_seq:
            return item_to_word_index

        alignment_pairs = self._align_sequences(
            [p for _, p in canonical_seq],
            [p for _, p in observed_seq],
        )

        for canonical_pos, observed_pos in alignment_pairs:

            if observed_pos is None:
                continue

            original_item_index = observed_seq[observed_pos][0]

            if canonical_pos is not None:
                word_index = canonical_seq[canonical_pos][0]
                item_to_word_index[original_item_index] = word_index

        # Fill any observed items that landed on a pure insertion-side
        # gap (canonical_pos is None) using the nearest neighbouring
        # assignment, so we don't leave holes in the middle of a word.
        # A leading gap (before any word has been assigned yet)
        # defaults to the first word, rather than being dropped.
        last_known: Optional[int] = 0 if canonical_seq else None

        for item_index, word_index in enumerate(item_to_word_index):

            if word_index is not None:
                last_known = word_index
                continue

            if item_index in [i for i, _ in observed_seq] and last_known is not None:
                item_to_word_index[item_index] = last_known

        return item_to_word_index

    # ------------------------------------------------------------------
    # Step 4: build the per-word breakdown
    # ------------------------------------------------------------------

    def _build_word_breakdown(
        self,
        words: List[str],
        items: List[Dict[str, Any]],
        item_to_word_index: List[Optional[int]],
        word_has_dict_entry: List[bool],
    ) -> List[Dict[str, Any]]:

        # Attach insertion items (no reference phoneme at all) to the
        # nearest preceding assigned item, so a spurious extra sound
        # is shown next to the word it interrupted. A leading insertion
        # (before any word has been assigned yet) defaults to the
        # first word, rather than being dropped.
        last_known: Optional[int] = 0 if words else None

        for item_index, item in enumerate(items):

            if item_to_word_index[item_index] is not None:
                last_known = item_to_word_index[item_index]
                continue

            if item.get("status") == "insertion" and last_known is not None:
                item_to_word_index[item_index] = last_known

        # Group item indices by word
        grouped: Dict[int, List[int]] = {
            i: [] for i in range(len(words))
        }

        for item_index, word_index in enumerate(item_to_word_index):
            if word_index is not None:
                grouped[word_index].append(item_index)

        breakdown: List[Dict[str, Any]] = []

        for word_index, word in enumerate(words):

            item_indices = grouped[word_index]
            word_items = [items[i] for i in item_indices]

            phoneme_scores = [
                float(it.get("phoneme_score", 0.0))
                for it in word_items
                if it.get("status") != "insertion"
            ]

            word_score = (
                round(sum(phoneme_scores) / len(phoneme_scores), 1)
                if phoneme_scores
                else None
            )

            issues = [
                {
                    "expected": it.get("expected"),
                    "actual": it.get("actual"),
                    "status": it.get("status"),
                    "phoneme_score": it.get("phoneme_score"),
                    "severity": it.get("severity"),
                    "evidence_status": it.get("evidence_status"),
                    "evidence_reason": it.get("evidence_reason"),
                    "l1_tip": it.get("l1_tip"),
                }
                for it in word_items
                if it.get("status") != "match"
            ]

            if word_score is None:
                status = "unscored"
            elif not word_has_dict_entry[word_index]:
                status = "unscored"
            elif word_score >= 85:
                status = "good"
            elif word_score >= 60:
                status = "needs_work"
            else:
                status = "error"

            breakdown.append(
                {
                    "word_index": word_index,
                    "word": word,
                    "score": word_score,
                    "status": status,
                    "phoneme_count": len(word_items),
                    "issue_count": len(issues),
                    "issues": issues,
                    "dictionary_coverage": word_has_dict_entry[word_index],
                }
            )

        return breakdown