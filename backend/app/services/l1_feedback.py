from typing import Dict, Optional, Tuple


class L1FeedbackService:
    """
    Maps known, research-documented L1 (native language) pronunciation
    transfer patterns to a short, plain-language tip.

    This is intentionally a simple, deterministic lookup table (not a
    model) — the same recommendation made in the BoldVoice-style
    industry blueprint: cheap, consistent, and avoids an LLM
    hallucinating corrective advice for something as sensitive as "why
    did I get this sound wrong".

    Extensible by design: each L1 is its own dict keyed by
    (expected_base_phoneme, actual_base_phoneme). Adding a new native
    language later is just adding another dict + registering it in
    _PATTERNS_BY_L1, no changes needed elsewhere in the pipeline.

    Sources for the Persian (fa) patterns below (see also the project
    handoff notes): published contrastive-analysis research on Iranian
    EFL learners' pronunciation — Moradi & Chen (2018, "A Contrastive
    Analysis of Persian and English Vowels and Consonants") for the
    vowel/consonant substitution pairs, and Akbari's dissertation on
    vowel epenthesis in initial consonant clusters by Persian speakers
    for the /s/-cluster pattern below. These are well-documented
    *tendencies*, not guarantees — every learner is different, which
    is exactly why this tip is shown as a possibility, not a diagnosis.
    """

    _PERSIAN_PATTERNS: Dict[Tuple[str, str], str] = {

        # --- /ð/ (voiced "th", as in "this") ---------------------------
        # Persian has no /ð/; it is commonly replaced with /d/ or /z/.
        ("dh", "d"): (
            "این صدا (th توی this/they) توی فارسی وجود نداره، برای همین "
            "معمولاً با d جایگزین می‌شه. نوک زبون رو بین دندون‌های بالا و "
            "پایین بذار و بذار هوا از همون‌جا رد بشه، به‌جای اینکه زبون رو "
            "به پشت دندون‌ها بچسبونی."
        ),
        ("dh", "z"): (
            "این صدا (th توی this/they) توی فارسی وجود نداره، برای همین "
            "معمولاً با z جایگزین می‌شه. نوک زبون رو بین دندون‌ها بذار، "
            "نه پشت دندون‌های پایین."
        ),

        # --- /θ/ (voiceless "th", as in "think") ------------------------
        # Persian has no /θ/; it is commonly replaced with /t/ (most
        # frequent) or /s/.
        ("th", "t"): (
            "این صدا (th توی think/thanks) توی فارسی وجود نداره، برای "
            "همین معمولاً با t جایگزین می‌شه. نوک زبون رو بین دندون‌ها "
            "بذار و بدون لرزش تارهای صوتی هوا رو بیرون بده."
        ),
        ("th", "s"): (
            "این صدا (th توی think/thanks) توی فارسی وجود نداره، برای "
            "همین بعضی‌وقتا با s جایگزین می‌شه. نوک زبون رو بین دندون‌ها "
            "بذار، نه پشت دندون‌های بالا."
        ),

        # --- /w/ ---------------------------------------------------------
        # Persian doesn't distinguish /w/ from /v/ the way English does.
        ("w", "v"): (
            "صدای w (مثل توی want) توی فارسی جدا از v وجود نداره، برای "
            "همین معمولاً با v قاطی می‌شه. لب‌ها رو گرد و کمی جلو ببر "
            "(مثل سوت زدن)، بدون اینکه لب پایین به دندون بالا بخوره."
        ),

        # --- vowel mergers ------------------------------------------------
        # English distinguishes many more vowels than Persian (~15 vs ~6),
        # so pairs like /ɪ/-/i:/ and /æ/-/e/ are commonly merged.
        ("ih", "iy"): (
            "صدای کوتاه ih (مثل توی sit) با صدای کشیده‌تر iy (مثل توی "
            "seat) قاطی شده. فارسی این تفاوت طول واکه رو نداره. سعی کن "
            "این صدا رو کوتاه‌تر و شل‌تر بگی، نه کامل مثل ای کشیده."
        ),
        ("ae", "eh"): (
            "صدای ae (مثل توی man) با صدای eh (مثل توی men) قاطی شده. "
            "برای ae فک باید بازتر باشه و زبون پایین‌تر و جلوتر بیاد."
        ),
        ("aa", "ao"): (
            "صدای aa (مثل توی hot/father) با صدای ao (مثل توی law/thought) "
            "قاطی شده. فارسی این دو واکه‌ی پشتی رو جدا از هم نداره. برای aa "
            "دهن باید بازتر باشه و لب‌ها گرد نشن؛ برای ao لب‌ها یکم گردتر "
            "و صدا بسته‌تره."
        ),
        ("uh", "uw"): (
            "صدای کوتاه uh (مثل توی book) با صدای کشیده‌تر uw (مثل توی "
            "boot) قاطی شده. فارسی این تفاوت طول واکه رو نداره. این صدا "
            "رو کوتاه‌تر و شل‌تر بگو، لب‌ها رو کمتر گرد کن."
        ),
        ("ay", "oy"): (
            "صدای دوحرکه‌ای ay (مثل توی my/time) با oy (مثل توی boy) "
            "قاطی شده. ay با دهن بازتر و بدون گرد کردن لب شروع می‌شه، "
            "در حالی که oy با لب‌های گردتر شروع می‌شه."
        ),
        ("ow", "ao"): (
            "صدای دوحرکه‌ای ow (مثل توی go/know) با ao (مثل توی law) "
            "قاطی شده. ow باید یه حرکت واضح به سمت uw داشته باشه (مثل "
            "او)، نه یه واکه‌ی ثابت."
        ),
    }

    # ------------------------------------------------------------------
    # Positional patterns (need surrounding context, not just a single
    # expected/actual pair) — also research-documented for Persian:
    #
    # - /ŋ/ is commonly followed by an extra /g/ that doesn't exist in
    #   English (e.g. "sing" -> "sing-g"), because Persian doesn't have
    #   a word-final /ŋ/ on its own.
    # - Persian syllables cannot start with a consonant cluster (only
    #   CV(C)), so learners commonly insert a vowel before/within an
    #   English word-initial cluster, especially /s/+consonant ones
    #   ("street" -> "estreet", "speak" -> "espeak"). This specific
    #   /s/-cluster case is the most error-prone per Akbari's cluster
    #   study, so that's the one pattern we detect here.
    # ------------------------------------------------------------------

    _NG_G_TIP = (
        "بعد از صدای ng (مثل توی sing) یه صدای g اضافه گفته شد. توی "
        "فارسی معمولاً بعد از این صدای بینی، g هم میاد (مثل «رنگ»)، ولی "
        "توی انگلیسی وقتی ng آخر کلمه‌ست، g نداره. فقط از بینی صدا رو "
        "تموم کن، لازم نیست زبون به سقف دهن بخوره."
    )

    _S_CLUSTER_EPENTHESIS_TIP = (
        "یه صدای واکه‌ی اضافه قبل از این کلمه گفته شد. توی فارسی هیچ "
        "کلمه‌ای با دو صامت پشت‌سرهم (مثل st, sp, sk) شروع نمی‌شه، برای "
        "همین زبان‌آموزهای فارسی‌زبان عادت دارن قبلش یه واکه اضافه کنن "
        "(مثلاً «street» رو «estreet» بگن). سعی کن مستقیم با صدای s "
        "شروع کنی، بدون هیچ واکه‌ای قبلش."
    )

    _PATTERNS_BY_L1: Dict[str, Dict[Tuple[str, str], str]] = {
        "fa": _PERSIAN_PATTERNS,
    }

    @staticmethod
    def _base_phoneme(phoneme: Optional[str]) -> Optional[str]:

        if not phoneme:
            return None

        return (
            phoneme[: -len("_err")]
            if phoneme.endswith("_err")
            else phoneme
        )

    def get_tip(
        self,
        expected: Optional[str],
        actual: Optional[str],
        status: Optional[str],
        l1: str = "fa",
    ) -> Optional[str]:
        """
        Returns a short Persian-language tip if this (expected, actual)
        substitution matches a known L1 transfer pattern, else None.

        Only substitutions are checked for now — deletions/insertions
        don't have a single "wrong sound" to explain in this simple
        pair-based model (e.g. consonant-cluster vowel epenthesis is a
        real, documented Persian-L1 pattern too, but needs a different,
        positional detection approach — left as a future improvement).
        """

        if status != "substitution":
            return None

        patterns = self._PATTERNS_BY_L1.get(l1)

        if not patterns:
            return None

        expected_base = self._base_phoneme(expected)
        actual_base = self._base_phoneme(actual)

        if not expected_base or not actual_base:
            return None

        return patterns.get((expected_base, actual_base))

    def get_positional_tips(
        self,
        items,
        word_index_map=None,
        l1: str = "fa",
    ):
        """
        Detects L1 patterns that need surrounding context, not just a
        single (expected, actual) pair — returns a list the same
        length as `items`, each entry either None or a tip string.

        Only implemented for Persian (fa) so far:
        - /ŋ/ followed by an inserted /g/.
        - A vowel inserted immediately before a word whose first two
          recognized reference phonemes are /s/ + another consonant
          (the most error-prone cluster type for Persian speakers).
        """

        tips = [None] * len(items)

        if l1 != "fa":
            return tips

        consonants = {
            "b", "ch", "d", "dh", "f", "g", "hh", "jh", "k", "l", "m",
            "n", "ng", "p", "r", "s", "sh", "t", "th", "v", "w", "y",
            "z", "zh",
        }
        vowels = {
            "aa", "ae", "ah", "ao", "aw", "ax", "ay", "eh", "er", "ey",
            "ih", "iy", "ow", "oy", "uh", "uw",
        }

        for i, item in enumerate(items):

            if item.get("status") != "insertion":
                continue

            actual_base = self._base_phoneme(item.get("actual"))

            if not actual_base:
                continue

            # --- /ŋ/ + inserted /g/ -------------------------------
            if actual_base == "g" and i > 0:

                prev_expected = self._base_phoneme(
                    items[i - 1].get("expected")
                )

                if prev_expected == "ng":
                    tips[i] = self._NG_G_TIP
                    continue

            # --- word-initial /s/-cluster vowel epenthesis --------
            if (
                actual_base in vowels
                and word_index_map is not None
                and i < len(word_index_map)
            ):

                this_word = word_index_map[i]
                prev_word = (
                    word_index_map[i - 1] if i > 0 else None
                )

                is_word_initial = (
                    this_word is not None and this_word != prev_word
                )

                if not is_word_initial:
                    continue

                next_expected = self._base_phoneme(
                    items[i + 1].get("expected")
                ) if i + 1 < len(items) else None

                after_next_expected = self._base_phoneme(
                    items[i + 2].get("expected")
                ) if i + 2 < len(items) else None

                if (
                    next_expected == "s"
                    and after_next_expected in consonants
                ):
                    tips[i] = self._S_CLUSTER_EPENTHESIS_TIP

        return tips