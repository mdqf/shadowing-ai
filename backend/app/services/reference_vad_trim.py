import io
import os
import tempfile
from typing import Any, Dict, Optional, Tuple

import librosa
import numpy as np
import soundfile as sf
import torch
from silero_vad import load_silero_vad, get_speech_timestamps


# Loaded once at import time (same pattern as the phoneme recognition
# model) — Silero VAD is small, but there is no reason to reload it
# on every request.
_VAD_MODEL = None


def _get_vad_model():

    global _VAD_MODEL

    if _VAD_MODEL is None:
        _VAD_MODEL = load_silero_vad()

    return _VAD_MODEL


class ReferenceVadTrimmer:
    """
    Subtitle timestamps are not reliable speech boundaries — they are
    timed for reading comfort, not audio precision, so a clip cut
    exactly at a subtitle's start/end can be missing the true onset of
    speech, or can bleed into the tail/head of the PREVIOUS or NEXT
    subtitle line's dialogue (this is especially likely for movie/TV
    audio with background music/sound effects, tight back-to-back
    dialogue, or auto-generated subtitles).

    This service expects the frontend to extract a slightly WIDER clip
    than the raw subtitle boundaries (some fixed padding on each
    side), plus the original subtitle start/end expressed as offsets
    into that padded clip ("anchor"). It then:

    1. Runs Silero VAD on the whole padded clip to find all
       contiguous speech segments.
    2. Picks the ONE segment that best corresponds to the anchor
       (the original subtitle window) — the segment containing the
       anchor's center, or if none does, the segment whose midpoint
       is closest to it.
    3. Trims the audio to that segment (with a small safety buffer),
       discarding anything before/after — which is exactly where
       bleed from an adjacent line would live.

    If VAD finds no speech at all (e.g. a very quiet or unusual clip),
    this falls back to returning the original, un-trimmed audio rather
    than risking cutting away real speech.
    """

    # Small buffer added around the selected VAD segment so we don't
    # clip the very onset/offset of a phoneme (VAD segment boundaries
    # are usually already a little conservative, but a small margin
    # is cheap insurance).
    SAFETY_BUFFER_SECONDS = 0.05

    def trim(
        self,
        audio_bytes: bytes,
        anchor_start: Optional[float],
        anchor_end: Optional[float],
    ) -> Tuple[bytes, Dict[str, Any]]:

        try:
            y, sr = librosa.load(
                io.BytesIO(audio_bytes),
                sr=16000,
                mono=True,
            )
        except Exception as load_error:
            return audio_bytes, {
                "applied": False,
                "reason": f"Could not decode audio: {load_error!r}",
            }

        clip_duration = len(y) / sr

        # Reference audio extracted from a video's own audio track is
        # often much quieter than a close-mic'd user recording (movie
        # mixing headroom, dialogue not being the loudest element,
        # etc.) — normalize its peak level so phoneme recognition and
        # any energy-based measurement isn't working with a low-SNR
        # signal. Applied to the whole clip up front so every return
        # path below (trimmed or not) benefits from it.
        y = self._normalize_gain(y)

        if anchor_start is None or anchor_end is None:
            anchor_start = 0.0
            anchor_end = clip_duration

        anchor_start = max(0.0, min(anchor_start, clip_duration))
        anchor_end = max(anchor_start, min(anchor_end, clip_duration))

        anchor_center = (anchor_start + anchor_end) / 2

        try:
            wav_tensor = torch.from_numpy(y)

            segments = get_speech_timestamps(
                wav_tensor,
                _get_vad_model(),
                sampling_rate=sr,
                return_seconds=True,
            )
        except Exception as vad_error:
            return self._encode_wav(y, sr), {
                "applied": False,
                "gain_normalized": True,
                "reason": f"VAD failed: {vad_error!r}",
            }

        if not segments:
            return self._encode_wav(y, sr), {
                "applied": False,
                "gain_normalized": True,
                "reason": "VAD found no speech in the clip.",
                "anchor_start": anchor_start,
                "anchor_end": anchor_end,
            }

        selected = self._select_segment(segments, anchor_center)

        trim_start = max(
            0.0, selected["start"] - self.SAFETY_BUFFER_SECONDS
        )
        trim_end = min(
            clip_duration, selected["end"] + self.SAFETY_BUFFER_SECONDS
        )

        start_sample = int(trim_start * sr)
        end_sample = int(trim_end * sr)

        trimmed_y = y[start_sample:end_sample]

        if len(trimmed_y) == 0:
            return self._encode_wav(y, sr), {
                "applied": False,
                "gain_normalized": True,
                "reason": "VAD-selected segment was empty after trim.",
            }

        trimmed_bytes = self._encode_wav(trimmed_y, sr)

        discarded_segments = [
            seg for seg in segments if seg is not selected
        ]

        return trimmed_bytes, {
            "applied": True,
            "gain_normalized": True,
            "clip_duration": round(clip_duration, 3),
            "anchor_start": round(anchor_start, 3),
            "anchor_end": round(anchor_end, 3),
            "all_speech_segments": [
                {
                    "start": round(seg["start"], 3),
                    "end": round(seg["end"], 3),
                }
                for seg in segments
            ],
            "selected_segment": {
                "start": round(selected["start"], 3),
                "end": round(selected["end"], 3),
            },
            "discarded_segment_count": len(discarded_segments),
            "trimmed_start": round(trim_start, 3),
            "trimmed_end": round(trim_end, 3),
        }

    @staticmethod
    def _select_segment(segments, anchor_center: float) -> Dict[str, float]:

        # Prefer a segment that actually contains the anchor center.
        containing = [
            seg
            for seg in segments
            if seg["start"] <= anchor_center <= seg["end"]
        ]

        if containing:
            return containing[0]

        # Otherwise, the segment whose midpoint is closest to it —
        # this is what correctly discards a neighboring subtitle
        # line's speech that also happened to fall inside the padded
        # clip.
        return min(
            segments,
            key=lambda seg: abs(
                (seg["start"] + seg["end"]) / 2 - anchor_center
            ),
        )

    @staticmethod
    def _normalize_gain(
        y: np.ndarray,
        target_peak: float = 0.95,
    ) -> np.ndarray:

        peak = float(np.max(np.abs(y))) if len(y) else 0.0

        if peak <= 0:
            return y

        return y * (target_peak / peak)

    @staticmethod
    def _encode_wav(y: np.ndarray, sr: int) -> bytes:

        buffer = io.BytesIO()
        sf.write(buffer, y, sr, format="WAV", subtype="PCM_16")
        return buffer.getvalue()