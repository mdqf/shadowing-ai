import os

from openai import OpenAI


class SpeechService:

    def __init__(self):

        api_key = os.getenv("AVALAI_API_KEY")

        if not api_key:
            raise RuntimeError(
                "AVALAI_API_KEY is not configured."
            )

        self.client = OpenAI(
            api_key=api_key,
            base_url="https://api.avalai.ir/v1",
        )

    def transcribe(
        self,
        audio_data: bytes,
        filename: str = "recording.webm",
        content_type: str = "audio/webm",
    ) -> dict:

        audio_file = (
            filename,
            audio_data,
            content_type,
        )

        transcription = self.client.audio.transcriptions.create(
            model="scribe_v2",
            file=audio_file,
        )

        # ==========================================
        # Basic transcription
        # ==========================================

        text = getattr(
            transcription,
            "text",
            "",
        )

        # ==========================================
        # Word timestamps
        # ==========================================

        raw_words = getattr(
            transcription,
            "words",
            None,
        )

        words = []

        if raw_words:

            for item in raw_words:

                # scribe_v2 returns each word as a dict
                if isinstance(item, dict):

                    word = item.get("word")
                    start = item.get("start")
                    end = item.get("end")

                else:

                    # Fallback for object-style responses
                    word = getattr(
                        item,
                        "word",
                        None,
                    )

                    start = getattr(
                        item,
                        "start",
                        None,
                    )

                    end = getattr(
                        item,
                        "end",
                        None,
                    )

                if word is None:
                    continue

                words.append({
                    "word": str(word),
                    "start": (
                        round(float(start), 3)
                        if start is not None
                        else None
                    ),
                    "end": (
                        round(float(end), 3)
                        if end is not None
                        else None
                    ),
                })

        # ==========================================
        # Result
        # ==========================================

        return {
            "text": text,
            "words": words,
        }