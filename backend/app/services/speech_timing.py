import re


class SpeechTimingService:

    def analyze(
        self,
        expected_text: str,
        transcribed_text: str,
        audio_analysis: dict,
    ) -> dict:

        # ==========================================
        # Normalize text
        # ==========================================

        expected_words = self._tokenize(expected_text)
        actual_words = self._tokenize(transcribed_text)

        expected_count = len(expected_words)
        actual_count = len(actual_words)

        # ==========================================
        # Audio values
        # ==========================================

        duration = float(
            audio_analysis.get("duration", 0)
        )

        speech_duration = float(
            audio_analysis
            .get("speech", {})
            .get("duration", 0)
        )

        silence_before = float(
            audio_analysis
            .get("silence", {})
            .get("before", 0)
        )

        silence_after = float(
            audio_analysis
            .get("silence", {})
            .get("after", 0)
        )

        pauses = audio_analysis.get(
            "pauses",
            []
        )

        # ==========================================
        # Speaking Rate
        # ==========================================

        if speech_duration > 0:
            actual_wpm = (
                actual_count
                / speech_duration
                * 60
            )
        else:
            actual_wpm = 0.0

        # ==========================================
        # Expected rate
        #
        # At this stage we don't know the original
        # video's exact speech timing, so we don't
        # invent an expected WPM.
        # ==========================================

        expected_wpm = None

        # ==========================================
        # Pause Analysis
        # ==========================================

        total_pause_duration = sum(
            float(pause.get("duration", 0))
            for pause in pauses
        )

        if duration > 0:
            pause_ratio = (
                total_pause_duration
                / duration
            )
        else:
            pause_ratio = 0.0

        # ==========================================
        # Speech Ratio
        # ==========================================

        if duration > 0:
            speech_ratio = (
                speech_duration
                / duration
            )
        else:
            speech_ratio = 0.0

        # ==========================================
        # Initial Response Delay
        # ==========================================

        initial_response_delay = silence_before

        # ==========================================
        # Final Silence Ratio
        # ==========================================

        if duration > 0:
            final_silence_ratio = (
                silence_after
                / duration
            )
        else:
            final_silence_ratio = 0.0

        # ==========================================
        # Average Pause
        # ==========================================

        if pauses:
            average_pause = (
                total_pause_duration
                / len(pauses)
            )
        else:
            average_pause = 0.0

        # ==========================================
        # Longest Pause
        # ==========================================

        if pauses:
            longest_pause = max(
                float(
                    pause.get(
                        "duration",
                        0,
                    )
                )
                for pause in pauses
            )
        else:
            longest_pause = 0.0

        # ==========================================
        # Result
        # ==========================================

        return {
            "words": {
                "expected": expected_count,
                "spoken": actual_count,
            },

            "rate": {
                "actual_wpm": round(
                    actual_wpm,
                    1,
                ),
                "expected_wpm": expected_wpm,
            },

            "speech_ratio": round(
                speech_ratio,
                3,
            ),

            "pause_ratio": round(
                pause_ratio,
                3,
            ),

            "pauses": {
                "count": len(pauses),
                "total_duration": round(
                    total_pause_duration,
                    3,
                ),
                "average_duration": round(
                    average_pause,
                    3,
                ),
                "longest_duration": round(
                    longest_pause,
                    3,
                ),
            },

            "response": {
                "initial_delay": round(
                    initial_response_delay,
                    3,
                ),
                "final_silence": round(
                    silence_after,
                    3,
                ),
                "final_silence_ratio": round(
                    final_silence_ratio,
                    3,
                ),
            },

            "duration": {
                "total": round(
                    duration,
                    3,
                ),
                "speech": round(
                    speech_duration,
                    3,
                ),
                "silence_before": round(
                    silence_before,
                    3,
                ),
                "silence_after": round(
                    silence_after,
                    3,
                ),
            },
        }

    # ==========================================
    # Tokenizer
    # ==========================================

    @staticmethod
    def _tokenize(text: str) -> list[str]:

        return re.findall(
            r"[a-zA-Z]+(?:'[a-zA-Z]+)?",
            text.lower(),
        )