import os
import subprocess
import tempfile
from typing import Any, Dict, List, Optional

import cmudict
import librosa
import numpy as np


VOWEL_PHONEMES = {
    "aa", "ae", "ah", "ao", "aw", "ax", "ay",
    "eh", "er", "ey", "ih", "iy", "ow", "oy", "uh", "uw",
}


class StressAnalysisService:
    """
    Lexical stress (prosody) scoring, v1.

    For each multi-syllable word, compares the CANONICAL stress
    pattern (from cmudict — which syllable is supposed to carry
    primary stress, e.g. te-RRI-fied) against which syllable the user
    ACTUALLY emphasized most, measured directly from their recording.

    Method:
    - "Syllable" = each vowel phoneme in the word (approximation).
    - "Emphasis" = a relative composite of duration + energy (+ pitch
      when it can be reliably measured) across that word's syllables,
      measured within each vowel's aligned time window in the user's
      audio. Stress is inherently a RELATIVE property within a word,
      so all measurements are z-scored against the other syllables of
      the same word, never compared across words.
    - Single-syllable words are skipped: there is no contrastive
      stress to evaluate for them.
    - If the number of syllables we could actually measure in the
      recording doesn't match the canonical syllable count (e.g. a
      vowel wasn't recognized), we still report the acoustic
      measurement for transparency, but mark the result as
      "index_reliable": False instead of guessing a mapping.

    This is a best-effort heuristic layer, not a validated clinical
    tool — pitch tracking on short (~50-150ms) vowel windows is
    inherently noisy, which is exactly why duration + energy (the
    two most robust correlates of stress) always contribute, with
    pitch as a bonus signal only when it can be extracted.
    """

    def __init__(self) -> None:
        self._cmu_dict = cmudict.dict()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def analyze(
        self,
        expected_text: str,
        items: List[Dict[str, Any]],
        item_to_word_index: List[Optional[int]],
        user_audio_bytes: bytes,
    ) -> List[Dict[str, Any]]:

        import re

        words = re.findall(r"[A-Za-z']+", expected_text or "")

        if not words or not items or not user_audio_bytes:
            return []

        y, sr = self._load_audio(user_audio_bytes)

        if y is None or len(y) == 0:
            return []

        results: List[Dict[str, Any]] = []

        for word_index, word in enumerate(words):

            canonical_stress = self._canonical_stress_pattern(word)

            if canonical_stress is None or len(canonical_stress) < 2:
                # Unknown word, or a single syllable: no contrastive
                # stress to evaluate.
                continue

            syllable_items = [
                (item_index, items[item_index])
                for item_index, w_idx in enumerate(item_to_word_index)
                if w_idx == word_index
                and items[item_index].get("status") in ("match", "substitution")
                and self._base(items[item_index].get("actual")) in VOWEL_PHONEMES
                and items[item_index].get("actual_timestamp")
            ]

            if len(syllable_items) < 2:
                results.append(
                    {
                        "word_index": word_index,
                        "word": word,
                        "canonical_syllable_count": len(canonical_stress),
                        "canonical_stress_syllable": self._primary_index(
                            canonical_stress
                        ),
                        "scored": False,
                        "reason": (
                            "Not enough recognized vowel sounds in the "
                            "recording to evaluate stress for this word."
                        ),
                    }
                )
                continue

            syllables = []

            for item_index, item in syllable_items:

                ts = item["actual_timestamp"]

                measurement = self._measure_prominence(
                    y=y,
                    sr=sr,
                    start=ts["start"],
                    end=ts["end"],
                )

                syllables.append(
                    {
                        "item_index": item_index,
                        "phoneme": item.get("actual"),
                        **measurement,
                    }
                )

            predicted_local_index = self._predict_stressed_syllable(syllables)

            index_reliable = len(syllables) == len(canonical_stress)

            canonical_index = self._primary_index(canonical_stress)

            stress_match = (
                (predicted_local_index == canonical_index)
                if index_reliable
                else None
            )

            results.append(
                {
                    "word_index": word_index,
                    "word": word,
                    "canonical_syllable_count": len(canonical_stress),
                    "canonical_stress_syllable": canonical_index,
                    "scored": True,
                    "index_reliable": index_reliable,
                    "detected_stress_syllable": predicted_local_index,
                    "stress_match": stress_match,
                    "syllables": syllables,
                }
            )

        return results

    # ------------------------------------------------------------------
    # Canonical stress (cmudict)
    # ------------------------------------------------------------------

    def _canonical_stress_pattern(self, word: str) -> Optional[List[int]]:
        """
        Returns the stress digit (0, 1, 2) of each VOWEL in the word's
        canonical cmudict pronunciation, in order. None if the word
        isn't in the dictionary.
        """

        clean = word.strip("'").lower()

        entries = self._cmu_dict.get(clean)

        if not entries:
            return None

        raw_phonemes = entries[0]

        stresses = []

        for phoneme in raw_phonemes:

            digits = [c for c in phoneme if c.isdigit()]

            if digits:
                stresses.append(int(digits[-1]))

        return stresses

    @staticmethod
    def _primary_index(stress_pattern: List[int]) -> int:

        if 1 in stress_pattern:
            return stress_pattern.index(1)

        # Fallback: no primary stress marked (rare) — treat the
        # first syllable as the reference point.
        return 0

    @staticmethod
    def _base(phoneme: Optional[str]) -> Optional[str]:

        if not phoneme:
            return None

        return (
            phoneme[: -len("_err")]
            if phoneme.endswith("_err")
            else phoneme
        )

    # ------------------------------------------------------------------
    # Acoustic measurement
    # ------------------------------------------------------------------

    def _measure_prominence(
        self,
        y: np.ndarray,
        sr: int,
        start: float,
        end: float,
    ) -> Dict[str, Optional[float]]:

        start_sample = max(int(start * sr), 0)
        end_sample = min(int(end * sr), len(y))

        segment = y[start_sample:end_sample]

        duration = round((end_sample - start_sample) / sr, 3)

        if len(segment) < 32:
            return {
                "duration": duration,
                "energy": 0.0,
                "pitch_hz": None,
            }

        energy = float(
            np.sqrt(np.mean(segment.astype(np.float64) ** 2))
        )

        pitch_hz = None

        # Pitch tracking on a very short window (a single vowel is
        # typically 50-150ms) is unreliable with the default frame
        # size, so we shrink it to fit and simply skip pitch (falling
        # back to duration + energy only) if it still can't be
        # measured — this is safer than reporting a noisy number.
        try:
            frame_length = min(1024, max(64, len(segment) // 2 * 2))

            if len(segment) >= frame_length:

                f0, _voiced_flag, _voiced_probs = librosa.pyin(
                    segment,
                    fmin=librosa.note_to_hz("C2"),
                    fmax=librosa.note_to_hz("C7"),
                    sr=sr,
                    frame_length=frame_length,
                )

                valid = f0[~np.isnan(f0)]

                if len(valid) > 0:
                    pitch_hz = float(np.mean(valid))

        except Exception:
            pitch_hz = None

        return {
            "duration": duration,
            "energy": round(energy, 6),
            "pitch_hz": (
                round(pitch_hz, 2) if pitch_hz is not None else None
            ),
        }

    @staticmethod
    def _predict_stressed_syllable(
        syllables: List[Dict[str, Any]],
    ) -> int:
        """
        Ranks syllables by a WEIGHTED composite of relative deviation
        (not z-score) in duration, energy, and (when available) pitch,
        all measured RELATIVE to the other syllables of the same word.
        Returns the local index (0-based, within this word) of the
        most prominent syllable.

        Two deliberate departures from a naive z-score composite:

        1. Relative deviation ((v - mean) / mean) instead of z-score
           ((v - mean) / std). Z-score normalizes by the sample's OWN
           spread, which throws away magnitude information — for a
           2-syllable word it mathematically always produces exactly
           +-1 for every feature regardless of whether the underlying
           difference is large or just measurement noise. Relative
           deviation preserves the true proportional size of the gap.

        2. Energy is weighted higher than duration and pitch. Energy
           (RMS) is the most direct, least noisy measurement we can
           take on a short (~50-150ms) vowel window. Duration is
           confounded by phrase-boundary lengthening (the last
           syllable of an utterance/phrase tends to lengthen
           regardless of stress), and pitch is confounded by the
           sentence's own intonation contour and is the hardest of
           the three to estimate reliably on such a short window.
        """

        ENERGY_WEIGHT = 1.5
        DURATION_WEIGHT = 0.6
        PITCH_WEIGHT = 0.6

        def relative_deviation(
            values: List[Optional[float]],
        ) -> List[float]:

            clean = [v for v in values if v is not None]

            if len(clean) < 2:
                return [0.0] * len(values)

            mean = sum(clean) / len(clean)

            if mean == 0:
                return [0.0] * len(values)

            return [
                (v - mean) / mean if v is not None else 0.0
                for v in values
            ]

        durations = [s["duration"] for s in syllables]
        energies = [s["energy"] for s in syllables]
        pitches = [s["pitch_hz"] for s in syllables]

        duration_rel = relative_deviation(durations)
        energy_rel = relative_deviation(energies)
        pitch_rel = relative_deviation(pitches)

        composite = [
            duration_rel[i] * DURATION_WEIGHT
            + energy_rel[i] * ENERGY_WEIGHT
            + pitch_rel[i] * PITCH_WEIGHT
            for i in range(len(syllables))
        ]

        return int(np.argmax(composite))

    # ------------------------------------------------------------------
    # Audio loading (mirrors AudioAnalysisService's WebM -> WAV path)
    # ------------------------------------------------------------------

    @staticmethod
    def _load_audio(audio_bytes: bytes):

        webm_path = None
        wav_path = None

        try:
            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".webm",
            ) as temp_file:

                temp_file.write(audio_bytes)
                webm_path = temp_file.name

            wav_path = webm_path + ".wav"

            ffmpeg_path = os.getenv("FFMPEG_PATH")

            if not ffmpeg_path or not os.path.exists(ffmpeg_path):
                return None, None

            subprocess.run(
                [
                    ffmpeg_path,
                    "-y",
                    "-i",
                    webm_path,
                    "-ac",
                    "1",
                    "-ar",
                    "16000",
                    "-c:a",
                    "pcm_s16le",
                    wav_path,
                ],
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )

            y, sr = librosa.load(
                wav_path,
                sr=None,
                mono=True,
            )

            return y, sr

        except Exception:
            return None, None

        finally:

            if webm_path and os.path.exists(webm_path):
                try:
                    os.remove(webm_path)
                except OSError:
                    pass

            if wav_path and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except OSError:
                    pass