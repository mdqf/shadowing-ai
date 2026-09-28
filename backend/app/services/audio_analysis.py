import os
import subprocess
import tempfile

import librosa
import numpy as np


class AudioAnalysisService:

    def analyze(self, audio_bytes: bytes) -> dict:

        webm_path = None
        wav_path = None

        try:
            # ==========================================
            # Save uploaded WebM temporarily
            # ==========================================

            with tempfile.NamedTemporaryFile(
                delete=False,
                suffix=".webm",
            ) as temp_file:

                temp_file.write(audio_bytes)

                webm_path = temp_file.name

            # ==========================================
            # Convert WebM -> WAV using FFmpeg
            # ==========================================

            wav_path = webm_path + ".wav"

            try:

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
                        webm_path,

                        # Mono audio
                        "-ac",
                        "1",

                        # 16 kHz is more than enough
                        # for our current analysis
                        "-ar",
                        "16000",

                        # PCM WAV
                        "-c:a",
                        "pcm_s16le",

                        wav_path,
                    ],
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                )

            except subprocess.CalledProcessError as error:

                ffmpeg_error = (
                    error.stderr
                    if error.stderr
                    else "Unknown FFmpeg error."
                )

                raise RuntimeError(
                    f"FFmpeg failed to convert audio: "
                    f"{ffmpeg_error}"
                )

            # ==========================================
            # Load converted WAV
            # ==========================================

            y, sr = librosa.load(
                wav_path,
                sr=None,
                mono=True,
            )

            if len(y) == 0:
                raise ValueError(
                    "Audio file is empty."
                )

            # ==========================================
            # Duration
            # ==========================================

            duration = len(y) / sr

            # ==========================================
            # RMS Energy
            # ==========================================

            rms = librosa.feature.rms(
                y=y
            )[0]

            rms_mean = float(
                np.mean(rms)
            )

            rms_max = float(
                np.max(rms)
            )

            # ==========================================
            # Silence / Speech Detection
            # ==========================================

            intervals = librosa.effects.split(
                y,
                top_db=30,
            )

            if len(intervals) > 0:

                speech_start_sample = (
                    intervals[0][0]
                )

                speech_end_sample = (
                    intervals[-1][1]
                )

                speech_start = (
                    speech_start_sample / sr
                )

                speech_end = (
                    speech_end_sample / sr
                )

                speech_duration = (
                    speech_end
                    - speech_start
                )

                silence_before = speech_start

                silence_after = (
                    duration
                    - speech_end
                )

            else:

                speech_start = 0.0
                speech_end = 0.0
                speech_duration = 0.0

                silence_before = duration
                silence_after = 0.0

            # ==========================================
            # Pitch / Fundamental Frequency (F0)
            # ==========================================

            f0, voiced_flag, voiced_probs = (
                librosa.pyin(
                    y,
                    fmin=librosa.note_to_hz("C2"),
                    fmax=librosa.note_to_hz("C7"),
                    sr=sr,
                )
            )

            valid_pitch = f0[
                ~np.isnan(f0)
            ]

            if len(valid_pitch) > 0:

                pitch_min = float(
                    np.min(valid_pitch)
                )

                pitch_max = float(
                    np.max(valid_pitch)
                )

                pitch_mean = float(
                    np.mean(valid_pitch)
                )

            else:

                pitch_min = None
                pitch_max = None
                pitch_mean = None

            # ==========================================
            # Internal Pauses
            # ==========================================

            pauses = []

            if len(intervals) > 1:

                for index in range(
                    1,
                    len(intervals),
                ):

                    previous_end = (
                        intervals[index - 1][1]
                        / sr
                    )

                    current_start = (
                        intervals[index][0]
                        / sr
                    )

                    pause_duration = (
                        current_start
                        - previous_end
                    )

                    # Ignore very short gaps.
                    # They are usually natural
                    # micro-gaps between sounds.
                    if pause_duration >= 0.15:

                        pauses.append({
                            "start": round(
                                previous_end,
                                3,
                            ),

                            "end": round(
                                current_start,
                                3,
                            ),

                            "duration": round(
                                pause_duration,
                                3,
                            ),
                        })

            # ==========================================
            # Result
            # ==========================================

            return {

                "duration": round(
                    duration,
                    3,
                ),

                "sample_rate": sr,

                "speech": {

                    "start": round(
                        speech_start,
                        3,
                    ),

                    "end": round(
                        speech_end,
                        3,
                    ),

                    "duration": round(
                        speech_duration,
                        3,
                    ),
                },

                "silence": {

                    "before": round(
                        silence_before,
                        3,
                    ),

                    "after": round(
                        silence_after,
                        3,
                    ),
                },

                "pauses": pauses,

                "energy": {

                    "rms_mean": round(
                        rms_mean,
                        5,
                    ),

                    "rms_max": round(
                        rms_max,
                        5,
                    ),
                },

                "pitch": {

                    "min_hz": (
                        round(
                            pitch_min,
                            2,
                        )
                        if pitch_min is not None
                        else None
                    ),

                    "max_hz": (
                        round(
                            pitch_max,
                            2,
                        )
                        if pitch_max is not None
                        else None
                    ),

                    "mean_hz": (
                        round(
                            pitch_mean,
                            2,
                        )
                        if pitch_mean is not None
                        else None
                    ),
                },
            }

        finally:

            # ==========================================
            # Cleanup temporary WebM
            # ==========================================

            if (
                webm_path
                and os.path.exists(webm_path)
            ):
                try:
                    os.remove(webm_path)
                except OSError:
                    pass

            # ==========================================
            # Cleanup temporary WAV
            # ==========================================

            if (
                wav_path
                and os.path.exists(wav_path)
            ):
                try:
                    os.remove(wav_path)
                except OSError:
                    pass
