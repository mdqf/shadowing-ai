import os
import subprocess
import tempfile

import librosa
import numpy as np

from app.services.word_matching import (
    tokenize,
    align_words_with_indices,
)


# ==========================================================
# Tuning constants
#
# These control how a raw MFCC/DTW distance is converted
# into a 0-100 pronunciation score. They were picked to give
# a reasonable-looking curve, not derived from labeled data.
# Revisit once we have real user recordings to calibrate
# against (e.g. a few "clearly good" vs "clearly bad" takes).
# ==========================================================

DISTANCE_SCALE = 45.0
MIN_SEGMENT_SAMPLES = 400  # ~25ms at 16kHz
WORD_PADDING_SECONDS = 0.04


class PronunciationAnalysisService:

    # ======================================================
    # Public API
    # ======================================================

    def analyze(
        self,
        expected_text: str,
        reference_audio_bytes: bytes,
        reference_text: str,
        reference_words: list[dict],
        user_audio_bytes: bytes,
        user_text: str,
        user_words: list[dict],
    ) -> dict:

        reference_y, reference_sr = self._load_audio(
            reference_audio_bytes,
            suffix=".ref",
        )

        user_y, user_sr = self._load_audio(
            user_audio_bytes,
            suffix=".user",
        )

        expected_tokens = tokenize(expected_text)
        reference_tokens = tokenize(reference_text)
        user_tokens = tokenize(user_text)

        # ==================================================
        # Align expected words to BOTH audio transcripts,
        # so we know which native-audio word and which
        # learner-audio word correspond to each expected word.
        # ==================================================

        reference_alignment = align_words_with_indices(
            expected_tokens,
            reference_tokens,
        )

        user_alignment = align_words_with_indices(
            expected_tokens,
            user_tokens,
        )

        reference_lookup = self._expected_index_lookup(
            reference_alignment
        )

        user_lookup = self._expected_index_lookup(
            user_alignment
        )

        reference_timestamps = self._map_timestamps(
            reference_tokens,
            reference_words,
        )

        user_timestamps = self._map_timestamps(
            user_tokens,
            user_words,
        )

        # ==================================================
        # Score each expected word
        # ==================================================

        word_results = []
        scored_values = []

        for expected_index, expected_word in enumerate(
            expected_tokens
        ):

            reference_entry = reference_lookup.get(
                expected_index
            )

            user_entry = user_lookup.get(
                expected_index
            )

            # No reliable reference audio for this word
            # (e.g. STT on the video clip didn't pick it up).
            if (
                not reference_entry
                or reference_entry["status"] != "correct"
                or not reference_entry["indices"]
            ):

                word_results.append({
                    "word": expected_word,
                    "score": None,
                    "reason": "reference_unavailable",
                })

                continue

            reference_span = self._span_from_indices(
                reference_timestamps,
                reference_entry["indices"],
            )

            if not reference_span:

                word_results.append({
                    "word": expected_word,
                    "score": None,
                    "reason": "reference_unavailable",
                })

                continue

            # Word was not detected in the learner's speech
            # at all (missing), or the aligner matched it to
            # something else entirely (replaced).
            if (
                not user_entry
                or user_entry["status"] == "missing"
            ):

                word_results.append({
                    "word": expected_word,
                    "score": 0.0,
                    "reason": "not_spoken",
                })

                scored_values.append(0.0)

                continue

            if (
                user_entry["status"] != "correct"
                or not user_entry["indices"]
            ):

                word_results.append({
                    "word": expected_word,
                    "score": 0.0,
                    "reason": "different_word",
                })

                scored_values.append(0.0)

                continue

            user_span = self._span_from_indices(
                user_timestamps,
                user_entry["indices"],
            )

            if not user_span:

                word_results.append({
                    "word": expected_word,
                    "score": None,
                    "reason": "timing_unavailable",
                })

                continue

            score = self._compare_segments(
                reference_y,
                reference_sr,
                reference_span,
                user_y,
                user_sr,
                user_span,
            )

            word_results.append({
                "word": expected_word,
                "score": round(score, 1),
                "reason": None,
            })

            scored_values.append(score)

        overall_score = (
            round(
                sum(scored_values) / len(scored_values),
                1,
            )
            if scored_values
            else None
        )

        return {
            "overall_score": overall_score,
            "words": word_results,
        }

    # ======================================================
    # Audio loading (WebM/Opus, WAV, etc. -> mono 16kHz)
    # ======================================================

    def _load_audio(
        self,
        audio_bytes: bytes,
        suffix: str,
    ):

        input_path = None
        wav_path = None

        try:

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
            ) as temp_file:

                temp_file.write(audio_bytes)
                input_path = temp_file.name

            wav_path = input_path + ".wav"

            ffmpeg_path = os.getenv("FFMPEG_PATH")

            if not ffmpeg_path:
                raise RuntimeError(
                    "FFMPEG_PATH is not configured."
                )

            if not os.path.exists(ffmpeg_path):
                raise RuntimeError(
                    f"FFmpeg executable not found: {ffmpeg_path}"
                )

            subprocess.run(
                [
                    ffmpeg_path,
                    "-y",
                    "-i",
                    input_path,
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

        except subprocess.CalledProcessError as error:

            ffmpeg_error = (
                error.stderr
                if error.stderr
                else "Unknown FFmpeg error."
            )

            raise RuntimeError(
                f"FFmpeg failed to convert audio: {ffmpeg_error}"
            )

        finally:

            for path in (input_path, wav_path):

                if path and os.path.exists(path):
                    try:
                        os.remove(path)
                    except OSError:
                        pass

    # ======================================================
    # Alignment helpers
    # ======================================================

    @staticmethod
    def _expected_index_lookup(
        alignment: list[dict],
    ) -> dict:

        lookup = {}

        for entry in alignment:

            for expected_index in entry["expected_indices"]:

                lookup[expected_index] = {
                    "status": entry["status"],
                    "indices": entry["actual_indices"],
                }

        return lookup

    @staticmethod
    def _map_timestamps(
        tokens: list[str],
        words: list[dict],
    ) -> list[dict | None]:

        # Positional pairing: tokenize(text) and the STT
        # words-with-timestamps list are both derived from
        # the same transcript and are expected to line up
        # index-for-index. If lengths disagree (rare, e.g.
        # punctuation-only tokens), we fall back gracefully
        # by leaving the extra tokens without a timestamp.

        count = min(len(tokens), len(words))

        timestamps: list[dict | None] = []

        for index in range(count):

            word = words[index]

            start = word.get("start")
            end = word.get("end")

            if start is None or end is None:
                timestamps.append(None)
                continue

            timestamps.append({
                "start": float(start),
                "end": float(end),
            })

        for _ in range(count, len(tokens)):
            timestamps.append(None)

        return timestamps

    @staticmethod
    def _span_from_indices(
        timestamps: list[dict | None],
        indices: list[int],
    ):

        starts = []
        ends = []

        for index in indices:

            if index >= len(timestamps):
                continue

            timestamp = timestamps[index]

            if timestamp is None:
                continue

            starts.append(timestamp["start"])
            ends.append(timestamp["end"])

        if not starts:
            return None

        return (min(starts), max(ends))

    # ======================================================
    # Segment comparison (MFCC + DTW)
    # ======================================================

    def _slice_segment(
        self,
        y: np.ndarray,
        sr: int,
        span: tuple,
    ) -> np.ndarray:

        start, end = span

        start_sample = max(
            0,
            int((start - WORD_PADDING_SECONDS) * sr),
        )

        end_sample = min(
            len(y),
            int((end + WORD_PADDING_SECONDS) * sr),
        )

        segment = y[start_sample:end_sample]

        if len(segment) < MIN_SEGMENT_SAMPLES:

            segment = np.pad(
                segment,
                (0, MIN_SEGMENT_SAMPLES - len(segment)),
            )

        return segment

    def _compare_segments(
        self,
        reference_y: np.ndarray,
        reference_sr: int,
        reference_span: tuple,
        user_y: np.ndarray,
        user_sr: int,
        user_span: tuple,
    ) -> float:

        reference_segment = self._slice_segment(
            reference_y,
            reference_sr,
            reference_span,
        )

        user_segment = self._slice_segment(
            user_y,
            user_sr,
            user_span,
        )

        reference_mfcc = librosa.feature.mfcc(
            y=reference_segment,
            sr=reference_sr,
            n_mfcc=13,
        )

        user_mfcc = librosa.feature.mfcc(
            y=user_segment,
            sr=user_sr,
            n_mfcc=13,
        )

        # Drop the 0th MFCC coefficient (overall loudness) so
        # scoring reflects timbre/articulation, not volume.
        reference_mfcc = reference_mfcc[1:]
        user_mfcc = user_mfcc[1:]

        cost_matrix, warp_path = librosa.sequence.dtw(
            X=reference_mfcc,
            Y=user_mfcc,
            metric="euclidean",
        )

        total_cost = float(cost_matrix[-1, -1])
        path_length = max(len(warp_path), 1)

        normalized_cost = total_cost / path_length

        score = 100.0 / (
            1.0 + (normalized_cost / DISTANCE_SCALE)
        )

        return max(0.0, min(100.0, score))
