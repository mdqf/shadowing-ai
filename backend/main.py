import uvicorn
from dotenv import load_dotenv

load_dotenv()

import requests
import os
import base64
import subprocess
import tempfile
import json
from fastapi import (
    FastAPI,
    File,
    UploadFile,
    Form,
    HTTPException,
)
from fastapi.middleware.cors import CORSMiddleware

from typing import Optional

from app.services.speech_timing import SpeechTimingService
from app.services.word_matching import compare_words
from app.services.audio_analysis import AudioAnalysisService
from app.services.speech_service import SpeechService
from app.services.reference_audio import ReferenceAudioService
from app.services.pronunciation_analysis import PronunciationAnalysisService
from app.services.phoneme_recognition import PhonemeRecognitionService
from app.services.phoneme_alignment import PhonemeAlignmentService
from app.services.audio_preprocessor import AudioPreprocessor
from app.services.pronunciation_evidence import PronunciationEvidenceService
from app.services.pronunciation_analysis_v2 import PronunciationAnalysisV2
from app.services.stress_analysis import StressAnalysisService
from app.services.reference_vad_trim import ReferenceVadTrimmer
from app.services.phoneme_matching import (
    align_phonemes,
    score_alignment,
    attach_timestamps,
)

# =========================================================
# Services
# =========================================================

speech_service = SpeechService()
audio_analysis_service = AudioAnalysisService()
speech_timing_service = SpeechTimingService()
reference_audio_service = ReferenceAudioService()
pronunciation_analysis_service = PronunciationAnalysisService()
phoneme_recognition_service = PhonemeRecognitionService()
phoneme_alignment_service = PhonemeAlignmentService()
audio_preprocessor = AudioPreprocessor()
pronunciation_evidence_service = PronunciationEvidenceService()
pronunciation_analysis_v2 = PronunciationAnalysisV2()
stress_analysis_service = StressAnalysisService()
reference_vad_trimmer = ReferenceVadTrimmer()


# =========================================================
# FastAPI App
# =========================================================

app = FastAPI(
    title="Shadowing AI",
    description="AI-powered English Shadowing Coach",
    version="0.1.0",
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Development only
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================================================
# Audio Preprocessing Test
# =========================================================


@app.post("/api/audio/preprocess")
async def preprocess_audio(
    audio: UploadFile = File(...),
):
    try:

        # -----------------------------------------------------
        # 1. Read uploaded audio
        # -----------------------------------------------------

        audio_bytes = await audio.read()

        if not audio_bytes:
            raise HTTPException(
                status_code=400,
                detail="Audio file is empty.",
            )

        # -----------------------------------------------------
        # 2. Preprocess
        # -----------------------------------------------------

        cleaned_audio, metadata = audio_preprocessor.preprocess(
            audio_bytes=audio_bytes,
            filename=audio.filename or "audio.webm",
        )

        # -----------------------------------------------------
        # 3. Return metadata only for now
        #
        # We don't integrate the cleaned audio into the
        # main pipeline until we verify the trimming.
        # -----------------------------------------------------

        return {
            "success": True,
            "metadata": metadata,
            "cleaned_audio_size": len(cleaned_audio),
        }

    except HTTPException:
        raise

    except Exception as error:

        print(
            "AUDIO PREPROCESSING ERROR:",
            repr(error),
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# =========================================================
# Phoneme Compare
# =========================================================


@app.post("/api/phoneme/compare")
async def compare_phonemes(
    reference_audio: UploadFile = File(...),
    user_audio: UploadFile = File(...),
):
    """
    Compare phonemes from reference/native audio
    with phonemes from the user's recording.

    Both audio files are preprocessed independently
    before phoneme recognition.
    """

    try:

        # =====================================================
        # 1. Read original audio files
        # =====================================================

        reference_bytes = await reference_audio.read()
        user_bytes = await user_audio.read()

        if not reference_bytes:
            raise HTTPException(
                status_code=400,
                detail="Reference audio is empty.",
            )

        if not user_bytes:
            raise HTTPException(
                status_code=400,
                detail="User audio is empty.",
            )

        # =====================================================
        # 2. Preprocess reference audio
        # =====================================================

        cleaned_reference, reference_preprocessing = audio_preprocessor.preprocess(
            audio_bytes=reference_bytes,
            filename=reference_audio.filename or "reference.webm",
        )

        # =====================================================
        # 3. Preprocess user audio
        # =====================================================

        cleaned_user, user_preprocessing = audio_preprocessor.preprocess(
            audio_bytes=user_bytes,
            filename=user_audio.filename or "recording.webm",
        )

        # =====================================================
        # 4. Recognize reference phonemes
        # =====================================================

        reference_result = phoneme_recognition_service.recognize(cleaned_reference)

        # =====================================================
        # 5. Recognize user phonemes
        # =====================================================

        user_result = phoneme_recognition_service.recognize(cleaned_user)

        # =====================================================
        # 6. Extract phoneme timestamps
        # =====================================================

        reference_phonemes = reference_result.get("phoneme_timestamps", [])

        user_phonemes = user_result.get("phoneme_timestamps", [])

        # =====================================================
        # 7. Align reference vs user
        # =====================================================

        alignment_result = phoneme_alignment_service.align(
            reference_phonemes=reference_phonemes,
            user_phonemes=user_phonemes,
        )

        evidence_result = (
            pronunciation_evidence_service.analyze(
                alignment_result
            )
        )

        pronunciation_analysis = pronunciation_analysis_v2.analyze(
            alignment_result=alignment_result,
            evidence_result=evidence_result,
        )

        # =====================================================
        # 8. Return complete result
        # =====================================================

        return {
            "reference": {
                "phonemes": reference_result.get("phonemes", ""),
                "phoneme_timestamps": reference_phonemes,
                "duration": reference_result.get("duration"),
                "sample_rate": reference_result.get("sample_rate"),
                "preprocessing": reference_preprocessing,
            },
            "user": {
                "phonemes": user_result.get("phonemes", ""),
                "phoneme_timestamps": user_phonemes,
                "duration": user_result.get("duration"),
                "sample_rate": user_result.get("sample_rate"),
                "preprocessing": user_preprocessing,
            },
            "alignment": alignment_result,
            "pronunciation_evidence": evidence_result,
            "pronunciation_analysis": pronunciation_analysis,
        }

    except HTTPException:
        raise

    except Exception as error:

        print(
            "PHONEME COMPARE ERROR:",
            repr(error),
        )

        raise HTTPException(
            status_code=500,
            detail=str(error),
        )


# =========================================================
# Phoneme Recognizer
# =========================================================


@app.post("/api/phoneme/recognize")
async def recognize_phonemes(
    audio: UploadFile = File(...),
):
    try:

        # =====================================================
        # 1. Read original audio
        # =====================================================

        audio_bytes = await audio.read()

        if not audio_bytes:
            raise HTTPException(
                status_code=400,
                detail="Audio file is empty.",
            )

        # =====================================================
        # 2. Remove leading/trailing silence
        #
        # IMPORTANT:
        # Preprocessing happens ONLY ONCE.
        # =====================================================

        cleaned_audio, preprocessing = audio_preprocessor.preprocess(
            audio_bytes=audio_bytes,
            filename=audio.filename or "recording.webm",
        )

        # =====================================================
        # 3. Phoneme recognition on CLEAN audio
        # =====================================================

        result = phoneme_recognition_service.recognize(cleaned_audio)

        # =====================================================
        # 4. Return recognition + preprocessing metadata
        # =====================================================

        result["preprocessing"] = preprocessing

        return result

    except HTTPException:
        raise

    except Exception as e:

        print(
            "PHONEME RECOGNITION ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Shadowing Analysis
# =========================================================


@app.post("/api/shadowing/analyze")
async def analyze_shadowing(
    audio: UploadFile = File(...),
    expected_text: str = Form(...),
    reference_audio: Optional[UploadFile] = File(None),
    reference_anchor_start: Optional[float] = Form(None),
    reference_anchor_end: Optional[float] = Form(None),
):
    try:
        acoustic_pronunciation_result = {"overall_score": 0, "words": []}

        # =====================================================
        # Read audio
        # =====================================================

        audio_bytes = await audio.read()

        if not audio_bytes:
            raise HTTPException(
                status_code=400,
                detail="Audio file is empty.",
            )

        # =====================================================
        # User Audio Preprocessing
        # =====================================================

        audio_bytes, user_preprocessing = audio_preprocessor.preprocess(
            audio_bytes=audio_bytes,
            filename=audio.filename or "recording.webm",
        )

        if not expected_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Expected text is required.",
            )

        # Reference audio (native-speaker clip cut from the
        # source video on the frontend) is optional. Without
        # it, we simply skip pronunciation scoring.
        reference_audio_bytes = (
            await reference_audio.read() if reference_audio is not None else None
        )

        if reference_audio_bytes is not None and not reference_audio_bytes:
            reference_audio_bytes = None

        reference_preprocessing = None
        reference_vad_info = None

        if reference_audio_bytes:

            # Step 1: VAD-based trim, anchored on the original
            # (possibly imprecise) subtitle timing, to reject any
            # bleed from the previous/next subtitle line that may
            # have been captured in the padded clip the frontend
            # sent.
            try:
                reference_audio_bytes, reference_vad_info = (
                    reference_vad_trimmer.trim(
                        audio_bytes=reference_audio_bytes,
                        anchor_start=reference_anchor_start,
                        anchor_end=reference_anchor_end,
                    )
                )
            except Exception as vad_error:
                print("REFERENCE VAD TRIM ERROR:", repr(vad_error))
                reference_vad_info = {
                    "applied": False,
                    "reason": f"Unhandled error: {vad_error!r}",
                }

            # Step 2: the existing silence-trim preprocessing, same
            # as before, now running on the VAD-cleaned clip.
            reference_audio_bytes, reference_preprocessing = (
                audio_preprocessor.preprocess(
                    audio_bytes=reference_audio_bytes,
                    filename=(
                        reference_audio.filename
                        if reference_audio is not None
                        else "reference.wav"
                    ),
                )
            )

        # =====================================================
        # 1. Speech To Text
        # =====================================================

        transcription_result = speech_service.transcribe(
            audio_data=audio_bytes,
            filename="recording.wav",
            content_type="audio/wav",
        )

        transcribed_text = transcription_result["text"]
        transcribed_words = transcription_result["words"]

        # =====================================================
        # 2. Word Matching
        # =====================================================

        matching_result = compare_words(
            expected_text=expected_text,
            transcribed_text=transcribed_text,
        )

        # =====================================================
        # 3. Audio Analysis
        # =====================================================

        audio_result = audio_analysis_service.analyze(audio_bytes)

        # =====================================================
        # 4. Speech Timing Analysis
        # =====================================================

        timing_result = speech_timing_service.analyze(
            expected_text=expected_text,
            transcribed_text=transcribed_text,
            audio_analysis=audio_result,
        )

        # =====================================================
        # 5. Pronunciation Analysis (word-level + overall)
        #
        # Only runs when the frontend supplied a reference
        # clip cut from the source video for this subtitle.
        # =====================================================

        pronunciation_result = None
        phoneme_alignment_result = None
        pronunciation_analysis_v2_result = None
        stress_analysis_result = None

        if reference_audio_bytes:

            reference_transcription = speech_service.transcribe(
                audio_data=reference_audio_bytes,
                filename="reference.wav",
                content_type="audio/wav",
            )

            pronunciation_result = pronunciation_analysis_service.analyze(
                expected_text=expected_text,
                reference_audio_bytes=reference_audio_bytes,
                reference_text=reference_transcription["text"],
                reference_words=reference_transcription["words"],
                user_audio_bytes=audio_bytes,
                user_text=transcribed_text,
                user_words=transcribed_words,
            )

            # =================================================
            # 6. Phoneme-level alignment
            #
            # The native-speaker clip is treated as the phonetic
            # reference. We compare the recognizer's phoneme
            # sequence against the learner's sequence with a
            # global edit-distance alignment. This is deliberately
            # kept separate from the old MFCC/DTW score for now:
            # the phoneme alignment is observable and debuggable.
            # =================================================

            reference_phonemes = phoneme_recognition_service.recognize(
                reference_audio_bytes
            )

            user_phonemes = phoneme_recognition_service.recognize(audio_bytes)

            reference_tokens = reference_phonemes["phonemes"].split()
            user_tokens = user_phonemes["phonemes"].split()

            # Use the production phoneme alignment service so that
            # confidence values and timestamps survive into the
            # evidence + V2 pronunciation pipeline.
            alignment_result = phoneme_alignment_service.align(
                reference_phonemes=reference_phonemes.get("phoneme_timestamps", []),
                user_phonemes=user_phonemes.get("phoneme_timestamps", []),
            )

            evidence_result = pronunciation_evidence_service.analyze(
                alignment_result
            )

            pronunciation_analysis_v2_result = pronunciation_analysis_v2.analyze(
                alignment_result=alignment_result,
                evidence_result=evidence_result,
                expected_text=expected_text,
            )

            # =================================================
            # 6b. Lexical stress (prosody) analysis
            #
            # Best-effort, and never allowed to break the main
            # response if the DSP measurement fails for any
            # reason (e.g. an unusually short recording).
            # =================================================

            try:
                stress_analysis_result = stress_analysis_service.analyze(
                    expected_text=expected_text,
                    items=pronunciation_analysis_v2_result["items"],
                    item_to_word_index=pronunciation_analysis_v2_result[
                        "word_index_map"
                    ],
                    user_audio_bytes=audio_bytes,
                )
            except Exception as stress_error:
                print(
                    "STRESS ANALYSIS ERROR:",
                    repr(stress_error),
                )
                stress_analysis_result = []

            # V2 is now the authoritative pronunciation score.
            # The legacy MFCC/DTW result is kept separately as
            # acoustic similarity data for debugging/research.
            acoustic_pronunciation_result = pronunciation_result

            pronunciation_result = {
                "overall_score": pronunciation_analysis_v2_result[
                    "summary"
                ]["pronunciation_score"],
                "words": [],
            }

            # Keep the legacy phoneme_alignment response for backward
            # compatibility with the current frontend while V2 is
            # integrated into the UI.
            phoneme_alignment = align_phonemes(
                expected=reference_tokens,
                actual=user_tokens,
            )

            reference_timestamp_list = [
                {"start": item.get("start"), "end": item.get("end")}
                if item.get("start") is not None and item.get("end") is not None
                else None
                for item in reference_phonemes.get("phoneme_timestamps", [])
            ]

            user_timestamp_list = [
                {"start": item.get("start"), "end": item.get("end")}
                if item.get("start") is not None and item.get("end") is not None
                else None
                for item in user_phonemes.get("phoneme_timestamps", [])
            ]

            phoneme_alignment = attach_timestamps(
                phoneme_alignment,
                reference_timestamp_list,
                user_timestamp_list,
            )

            phoneme_alignment_result = {
                "reference": {
                    "phonemes": reference_tokens,
                    "duration": reference_phonemes["duration"],
                },
                "user": {
                    "phonemes": user_tokens,
                    "duration": user_phonemes["duration"],
                },
                "score": score_alignment(
                    phoneme_alignment,
                    len(reference_tokens),
                ),
                "statistics": {
                    "reference": len(reference_tokens),
                    "user": len(user_tokens),
                    "match": sum(1 for item in phoneme_alignment if item["status"] == "match"),
                    "substitution": sum(1 for item in phoneme_alignment if item["status"] == "substitution"),
                    "deletion": sum(1 for item in phoneme_alignment if item["status"] == "deletion"),
                    "insertion": sum(1 for item in phoneme_alignment if item["status"] == "insertion"),
                },
                "alignment": phoneme_alignment,
            }

        # =====================================================
        # 6. Unified Response
        # =====================================================

        # Debug audio: the EXACT trimmed WAV bytes that were
        # analyzed (post audio_preprocessor.preprocess()), so their
        # timestamps line up with everything in this response. Only
        # for local debugging/export — not used by the UI otherwise.
        try:
            user_audio_base64 = (
                base64.b64encode(audio_bytes).decode("ascii")
                if audio_bytes
                else None
            )
        except Exception:
            user_audio_base64 = None

        try:
            reference_audio_base64 = (
                base64.b64encode(reference_audio_bytes).decode("ascii")
                if reference_audio_bytes
                else None
            )
        except Exception:
            reference_audio_base64 = None

        return {
            "expected_text": expected_text,
            "transcribed_text": transcribed_text,
            "transcribed_words": transcribed_words,
            "matching": matching_result,
            "audio": audio_result,
            "timing": timing_result,
            "pronunciation": pronunciation_result,
            "acoustic_pronunciation": acoustic_pronunciation_result,
            "phoneme_alignment": phoneme_alignment_result,
            "pronunciation_analysis_v2": pronunciation_analysis_v2_result,
            "stress_analysis": stress_analysis_result,
            "preprocessing": {
                "user": user_preprocessing,
                "reference": reference_preprocessing,
                "reference_vad": reference_vad_info,
            },
            "debug_audio": {
                "user_wav_base64": user_audio_base64,
                "reference_wav_base64": reference_audio_base64,
            },
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "SHADOWING ANALYSIS ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Reference Audio Analysis
# =========================================================


@app.post("/api/reference/analyze")
async def analyze_reference(audio: UploadFile = File(...)):

    try:

        audio_bytes = await audio.read()

        if not audio_bytes:
            raise HTTPException(status_code=400, detail="Reference audio is empty.")

        result = reference_audio_service.analyze(audio_bytes)

        return result

    except HTTPException:
        raise

    except Exception as e:

        print("REFERENCE AUDIO ANALYSIS ERROR:", repr(e))

        raise HTTPException(status_code=500, detail=str(e))


# =========================================================
# Audio Analysis
# =========================================================


@app.post("/api/speech/analyze")
async def analyze_speech(
    audio: UploadFile = File(...),
):

    try:

        audio_bytes = await audio.read()

        if not audio_bytes:
            raise HTTPException(
                status_code=400,
                detail="Audio file is empty.",
            )

        cleaned_audio, preprocessing = audio_preprocessor.preprocess(
            audio_bytes=audio_bytes,
            filename=audio.filename or "recording.webm",
        )

        result = audio_analysis_service.analyze(cleaned_audio)

        result["preprocessing"] = preprocessing

        return result

    except HTTPException:
        raise

    except Exception as e:

        print(
            "AUDIO ANALYSIS ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Speech Transcription + Word Matching
# =========================================================


@app.post("/api/speech/transcribe")
async def transcribe_speech(
    audio: UploadFile = File(...),
    expected_text: str = Form(...),
):

    try:

        audio_data = await audio.read()

        if not audio_data:
            raise HTTPException(
                status_code=400,
                detail="Audio file is empty.",
            )

        if not expected_text.strip():
            raise HTTPException(
                status_code=400,
                detail="Expected text is required.",
            )

        cleaned_audio, preprocessing = audio_preprocessor.preprocess(
            audio_bytes=audio_data,
            filename=audio.filename or "recording.webm",
        )

        transcription_result = speech_service.transcribe(
            audio_data=cleaned_audio,
            filename="recording.wav",
            content_type="audio/wav",
        )

        transcribed_text = transcription_result["text"]

        comparison = compare_words(
            expected_text=expected_text,
            transcribed_text=transcribed_text,
        )

        return {
            "expected_text": expected_text,
            "transcribed_text": transcribed_text,
            "transcribed_words": transcription_result["words"],
            "matching": comparison,
            "preprocessing": preprocessing,
        }

    except HTTPException:
        raise

    except Exception as e:

        print(
            "STT ERROR:",
            repr(e),
        )

        raise HTTPException(
            status_code=500,
            detail=str(e),
        )


# =========================================================
# Root
# =========================================================


@app.get("/")
def root():

    return {"message": "Shadowing AI API is running"}


# =========================================================
# Health Check
# =========================================================


@app.get("/health")
def health():

    return {"status": "ok"}


# =========================================================
# Subtitle Extractor
# =========================================================


@app.post("/api/subtitles/extract")
async def extract_subtitles_from_video(file: UploadFile = File(...)):
    """استخراج هوشمند زیرنویس انگلیسی از فایل‌های MKV/MP4 چند زبانه"""
    try:
        suffix = os.path.splitext(file.filename or "")[1] or ".mkv"
        with tempfile.NamedTemporaryFile(
            delete=False, suffix=suffix
        ) as tmp_video:
            content = await file.read()
            tmp_video.write(content)
            tmp_video_path = tmp_video.name

        output_srt_path = tmp_video_path + ".srt"

        # ۱. آنالیز ترک‌های صوتی و زیرنویس ویدیو با ffprobe
        ffprobe_cmd = [
            "ffprobe",
            "-v",
            "quiet",
            "-print_format",
            "json",
            "-show_streams",
            "-select_streams",
            "s",  # فقط استریم‌های زیرنویس
            tmp_video_path,
        ]

        probe_result = subprocess.run(
            ffprobe_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        subtitle_streams = []

        if probe_result.returncode == 0 and probe_result.stdout:
            try:
                probe_data = json.loads(probe_result.stdout.decode("utf-8"))
                subtitle_streams = probe_data.get("streams", [])
            except Exception as json_err:
                print("FFprobe JSON error:", json_err)

        # ۲. یافتن اندیس ترک انگلیسی
        target_map = None

        # الف) جستجو بر اساس زبان یا عنوان (English/eng/en)
        for stream in subtitle_streams:
            tags = stream.get("tags", {})
            lang = (tags.get("language") or tags.get("lang") or "").lower()
            title = (tags.get("title") or "").lower()

            if (
                "eng" in lang
                or "en" in lang
                or "english" in title
                or "eng" in title
            ):
                target_map = f"0:{stream.get('index')}"
                break

        # ب) در صورت عدم وجود برچسب زبان، انتخاب اولین ترکی که فارسی نباشد
        if not target_map and subtitle_streams:
            for stream in subtitle_streams:
                tags = stream.get("tags", {})
                lang = (tags.get("language") or tags.get("lang") or "").lower()
                title = (tags.get("title") or "").lower()

                if (
                    "per" not in lang
                    and "fas" not in lang
                    and "fa" not in lang
                    and "persian" not in title
                    and "farsi" not in title
                ):
                    target_map = f"0:{stream.get('index')}"
                    break

        # ج) در صورت عدم شناسایی، استفاده از مپ پیش‌فرض برای ترک‌های انگلیسی
        if not target_map:
            target_map = "0:m:language:eng?"

        # ۳. استخراج ترک انتخاب‌شده با FFmpeg
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            tmp_video_path,
            "-map",
            target_map,
            output_srt_path,
        ]

        subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

        # ۴. خواندن محتوای فایل SRT حاصل
        if (
            os.path.exists(output_srt_path)
            and os.path.getsize(output_srt_path) > 0
        ):
            with open(
                output_srt_path, "r", encoding="utf-8", errors="ignore"
            ) as f:
                srt_content = f.read()

            os.remove(tmp_video_path)
            os.remove(output_srt_path)

            return {"status": "success", "srt_content": srt_content}

        else:
            if os.path.exists(tmp_video_path):
                os.remove(tmp_video_path)
            if os.path.exists(output_srt_path):
                os.remove(output_srt_path)
            raise HTTPException(
                status_code=400,
                detail="امکان استخراج زیرنویس انگلیسی از این فایل ویدیو وجود نداشت.",
            )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"خطا در استخراج زیرنویس: {str(e)}"
        )


# =========================================================
# AvalAI Credit Balance
# =========================================================

@app.get("/api/avalai/credit")
async def get_avalai_credit():
    """
    دریافت موجودی اعتبار AvalAI
    """
    api_key = os.getenv("AVALAI_API_KEY")
    if not api_key:
        raise HTTPException(
            status_code=500,
            detail="AVALAI_API_KEY is not configured."
        )

    url = "https://api.avalai.ir/user/v1/credit"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"AvalAI API error: {http_err}"
        )
    except Exception as err:
        print("AVALAI CREDIT ERROR:", repr(err))
        raise HTTPException(
            status_code=500,
            detail=str(err)
        )


# =========================================================
# Development Server
# =========================================================

if __name__ == "__main__":

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
    )