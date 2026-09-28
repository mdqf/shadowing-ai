import io
import subprocess

import numpy as np
import torch
import torch.nn.functional as F
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
from app.services.ctc_alignment import CTCAlignmentService


MODEL_NAME = "slplab/wav2vec2-large-robust-L2-english-phoneme-recognition"


class PhonemeRecognitionService:
    """
    NOTE ON STARTUP TIME: loading this model (wav2vec2-large) used to
    happen eagerly in __init__, which runs at server import time —
    before uvicorn could even start accepting connections. It is now
    LAZY: __init__ is instant, and the actual model load happens once,
    on the first call to recognize() (or any method that needs it).
    This means `uvicorn --reload` / server startup is fast, and the
    one-time model-loading delay instead happens on the first real
    analysis request after startup.

    GPU note: this already auto-selects CUDA when available
    (torch.cuda.is_available()) and always did — a GPU speeds up each
    recognize() CALL (inference), not the one-time model *loading*
    itself, so it does not by itself fix a slow startup. If
    torch.cuda.is_available() is False on your machine, this is still
    running on CPU regardless of this change; check with:
        python -c "import torch; print(torch.cuda.is_available())"
    """

    def __init__(self):
        self.processor = None
        self.model = None
        self.aligner = None
        self.device = None
        self._loaded = False

    def _ensure_loaded(self):

        if self._loaded:
            return

        print("Loading phoneme recognition model...")

        self.processor = Wav2Vec2Processor.from_pretrained(MODEL_NAME)
        self.model = Wav2Vec2ForCTC.from_pretrained(MODEL_NAME)

        self.aligner = CTCAlignmentService(
            self.processor
        )

        self.model.eval()

        self.device = torch.device(
            "cuda" if torch.cuda.is_available() else "cpu"
        )

        self.model.to(self.device)

        self._loaded = True

        print(f"Phoneme model loaded on: {self.device}")

    def _decode_audio_with_ffmpeg(self, audio_data: bytes) -> tuple[np.ndarray, int]:
        """
        Decode any browser-supported audio format (e.g. WebM/Opus)
        into 16 kHz mono float32 PCM using the system FFmpeg.
        """

        command = [
            "ffmpeg",
            "-hide_banner",
            "-loglevel",
            "error",

            # Input comes from memory.
            "-i",
            "pipe:0",

            # Output:
            "-f",
            "f32le",
            "-acodec",
            "pcm_f32le",
            "-ac",
            "1",
            "-ar",
            "16000",

            "pipe:1",
        ]

        process = subprocess.run(
            command,
            input=audio_data,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )

        if process.returncode != 0:
            error_message = process.stderr.decode(
                "utf-8",
                errors="replace",
            )

            raise RuntimeError(
                f"FFmpeg audio decoding failed:\n{error_message}"
            )

        if not process.stdout:
            raise RuntimeError(
                "FFmpeg returned empty audio data."
            )

        waveform = np.frombuffer(
            process.stdout,
            dtype=np.float32,
        ).copy()

        if waveform.size == 0:
            raise RuntimeError(
                "Decoded waveform is empty."
            )

        return waveform, 16000

    def recognize(self, audio_data: bytes) -> dict:
        """
        Convert uploaded audio into phonemes and
        align the recognized phonemes using CTC.
        """

        self._ensure_loaded()

        waveform, sample_rate = self._decode_audio_with_ffmpeg(
            audio_data
        )
    
        duration = len(waveform) / sample_rate
    
        inputs = self.processor(
            waveform,
            sampling_rate=sample_rate,
            return_tensors="pt",
        )
    
        input_values = inputs.input_values.to(self.device)
    
        attention_mask = None
    
        if hasattr(inputs, "attention_mask"):
            attention_mask = inputs.attention_mask.to(self.device)
    
        with torch.no_grad():
            outputs = self.model(
                input_values=input_values,
                attention_mask=attention_mask,
            )
    
        logits = outputs.logits

        # ---------------------------------------------------------
        # CTC frame-level probabilities
        # ---------------------------------------------------------

        log_probs = F.log_softmax(logits, dim=-1)
        probs = log_probs.exp()

        predicted_ids = torch.argmax(logits, dim=-1)

        frame_confidences = []

        for frame_index, token_id in enumerate(predicted_ids[0]):
            confidence = probs[
                0,
                frame_index,
                token_id
            ].item()

            frame_confidences.append(confidence)

        predicted_ids = torch.argmax(
            logits,
            dim=-1,
        )
    
        # Decode phoneme sequence.
        phonemes_text = self.processor.decode(
            predicted_ids[0].cpu()
        )
    
        # Convert:
        # "hh eh l ow hh aw aa r y uw"
        #
        # into:
        # ["hh", "eh", "l", "ow", ...]
        phonemes = phonemes_text.split()
    
        # CTC forced alignment.

        phoneme_timestamps = self.aligner.align(
            logits=logits,
            phonemes=phonemes,
            duration=duration,
            frame_confidences=frame_confidences,
        )
  
        return {
            "phonemes": phonemes_text,
            "phoneme_timestamps": phoneme_timestamps,
            "sample_rate": sample_rate,
            "duration": round(duration, 3),
            "num_frames": int(logits.shape[1]),
        }