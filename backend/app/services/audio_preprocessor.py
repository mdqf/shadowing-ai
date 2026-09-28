import io
import os
import subprocess
import tempfile

import librosa
import numpy as np
import soundfile as sf


class AudioPreprocessor:

    def __init__(
        self,
        target_sample_rate: int = 16000,
        top_db: int = 30,
        padding_ms: int = 100,
    ):
        self.target_sample_rate = target_sample_rate
        self.top_db = top_db
        self.padding_ms = padding_ms

    def preprocess(
        self,
        audio_bytes: bytes,
        filename: str = "audio.webm",
    ) -> tuple[bytes, dict]:

        if not audio_bytes:
            raise ValueError("Audio file is empty.")

        original_duration = 0.0

        input_path = None
        wav_path = None

        try:
            # =====================================================
            # 1. Save uploaded audio temporarily
            # =====================================================

            extension = os.path.splitext(filename)[1]

            if not extension:
                extension = ".webm"

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=extension,
            ) as temp_file:

                temp_file.write(audio_bytes)
                input_path = temp_file.name

            # =====================================================
            # 2. Convert to WAV / 16 kHz / Mono
            #
            # We use FFmpeg because uploaded audio can be:
            # WebM, MKV, MP4, M4A, etc.
            # =====================================================

            ffmpeg_path = os.getenv("FFMPEG_PATH")

            if not ffmpeg_path:
                raise RuntimeError("FFMPEG_PATH is not configured.")

            if not os.path.exists(ffmpeg_path):
                raise RuntimeError(f"FFmpeg executable not found: {ffmpeg_path}")

            wav_path = input_path + ".wav"

            subprocess.run(
                [
                    ffmpeg_path,
                    "-y",
                    "-i",
                    input_path,
                    "-ac",
                    "1",
                    "-ar",
                    str(self.target_sample_rate),
                    "-vn",
                    wav_path,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=True,
            )

            # =====================================================
            # 3. Load WAV
            # =====================================================

            y, sr = librosa.load(
                wav_path,
                sr=self.target_sample_rate,
                mono=True,
            )

            if len(y) == 0:
                raise ValueError("Audio contains no samples.")

            original_duration = len(y) / sr

            # =====================================================
            # 4. Detect non-silent regions
            #
            # This is energy-based silence detection.
            # It is NOT a neural VAD.
            # =====================================================

            intervals = librosa.effects.split(
                y,
                top_db=self.top_db,
                frame_length=2048,
                hop_length=512,
            )

            # =====================================================
            # 5. If nothing is detected
            #
            # Do not destroy the user's audio.
            # Return the original decoded audio.
            # =====================================================

            if len(intervals) == 0:

                output_bytes = self._encode_wav(
                    y=y,
                    sample_rate=sr,
                )

                metadata = {
                    "trimmed": False,
                    "reason": "no_non_silent_region_detected",
                    "original_duration": round(
                        original_duration,
                        3,
                    ),
                    "trimmed_duration": round(
                        original_duration,
                        3,
                    ),
                    "leading_silence": 0.0,
                    "trailing_silence": 0.0,
                    "trim_start": 0.0,
                    "trim_end": round(
                        original_duration,
                        3,
                    ),
                    "padding": 0.0,
                    "sample_rate": sr,
                }

                return output_bytes, metadata

            # =====================================================
            # 6. Determine actual speech region
            # =====================================================

            speech_start_sample = intervals[0][0]
            speech_end_sample = intervals[-1][1]

            speech_start = speech_start_sample / sr

            speech_end = speech_end_sample / sr

            # =====================================================
            # 7. Safety padding
            #
            # We intentionally keep a small amount of audio
            # around speech so that phoneme attacks are not cut.
            # =====================================================

            padding = self.padding_ms / 1000.0

            trim_start = max(
                0.0,
                speech_start - padding,
            )

            trim_end = min(
                original_duration,
                speech_end + padding,
            )

            # =====================================================
            # 8. Convert times -> samples
            # =====================================================

            start_sample = max(
                0,
                int(round(trim_start * sr)),
            )

            end_sample = min(
                len(y),
                int(round(trim_end * sr)),
            )

            if end_sample <= start_sample:
                raise ValueError("Invalid trimming boundaries.")

            # =====================================================
            # 9. Trim
            # =====================================================

            trimmed_y = y[start_sample:end_sample]

            trimmed_duration = len(trimmed_y) / sr

            # =====================================================
            # 10. Actual removed silence
            # =====================================================

            leading_silence = trim_start

            trailing_silence = original_duration - trim_end

            # =====================================================
            # 11. Encode cleaned audio as WAV
            # =====================================================

            output_bytes = self._encode_wav(
                y=trimmed_y,
                sample_rate=sr,
            )

            # =====================================================
            # 12. Metadata
            # =====================================================

            metadata = {
                "trimmed": True,
                "original_duration": round(
                    original_duration,
                    3,
                ),
                "trimmed_duration": round(
                    trimmed_duration,
                    3,
                ),
                "leading_silence": round(
                    leading_silence,
                    3,
                ),
                "trailing_silence": round(
                    trailing_silence,
                    3,
                ),
                "trim_start": round(
                    trim_start,
                    3,
                ),
                "trim_end": round(
                    trim_end,
                    3,
                ),
                "speech_start": round(
                    speech_start,
                    3,
                ),
                "speech_end": round(
                    speech_end,
                    3,
                ),
                "padding": round(
                    padding,
                    3,
                ),
                "sample_rate": sr,
            }

            return output_bytes, metadata

        finally:

            # =====================================================
            # Cleanup input file
            # =====================================================

            if input_path and os.path.exists(input_path):
                try:
                    os.remove(input_path)
                except OSError:
                    pass

            # =====================================================
            # Cleanup WAV
            # =====================================================

            if wav_path and os.path.exists(wav_path):
                try:
                    os.remove(wav_path)
                except OSError:
                    pass

    # =========================================================
    # WAV Encoder
    # =========================================================

    @staticmethod
    def _encode_wav(
        y: np.ndarray,
        sample_rate: int,
    ) -> bytes:

        buffer = io.BytesIO()

        sf.write(
            buffer,
            y.astype(np.float32),
            sample_rate,
            format="WAV",
            subtype="PCM_16",
        )

        buffer.seek(0)

        return buffer.read()
