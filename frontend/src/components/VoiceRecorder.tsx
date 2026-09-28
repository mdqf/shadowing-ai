import React, { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useParams, useNavigate } from "react-router-dom";
import {
  Box,
  Paper,
  Typography,
  Button,
  IconButton,
  Chip,
  CircularProgress,
  Divider,
  Stack,
  Tooltip as MuiTooltip,
  ToggleButton,
  ToggleButtonGroup,
  Alert,
  Switch,
  FormControlLabel,
} from "@mui/material";

import ArrowBackRoundedIcon from "@mui/icons-material/ArrowBackRounded";
import MicRoundedIcon from "@mui/icons-material/MicRounded";
import StopRoundedIcon from "@mui/icons-material/StopRounded";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import ReplayRoundedIcon from "@mui/icons-material/ReplayRounded";
import CheckRoundedIcon from "@mui/icons-material/CheckRounded";
import Replay10RoundedIcon from "@mui/icons-material/Replay10Rounded";
import SkipNextRoundedIcon from "@mui/icons-material/SkipNextRounded";
import SkipPreviousRoundedIcon from "@mui/icons-material/SkipPreviousRounded";
import VolumeUpRoundedIcon from "@mui/icons-material/VolumeUpRounded";
import MovieRoundedIcon from "@mui/icons-material/MovieRounded";
import SubtitlesRoundedIcon from "@mui/icons-material/SubtitlesRounded";
import DownloadRoundedIcon from "@mui/icons-material/DownloadRounded";
import LightbulbRoundedIcon from "@mui/icons-material/LightbulbRounded";
import GraphicEqRoundedIcon from "@mui/icons-material/GraphicEqRounded";

import { extractAudioClip } from "../utils/audioClip";
import { parseSRT } from "../utils/srtParser";
import type { SubtitleItem } from "../utils/srtParser";
import { COURSES_DATA } from "../data/coursesData";
import "./VoiceRecorder.css";

const API_BASE_URL = "http://localhost:8000";

// =========================================================
// Types
// =========================================================

type MatchStatus = "correct" | "missing" | "extra" | "replaced";
type MatchType = "exact" | "normalized" | "none";

type WordMatch = {
  expected: string[];
  actual: string[];
  status: MatchStatus;
  match_type: MatchType;
};

type ComparisonStatistics = {
  total_expected: number;
  correct: number;
  missing: number;
  extra: number;
  replaced: number;
};

type MatchingResult = {
  expected_text: string;
  transcribed_text: string;
  matches: WordMatch[];
  statistics: ComparisonStatistics;
  accuracy: number;
};

type AudioPause = { start: number; end: number; duration: number };

type AudioAnalysis = {
  duration: number;
  sample_rate: number;
  speech: { start: number; end: number; duration: number };
  silence: { before: number; after: number };
  pauses: AudioPause[];
  energy: { rms_mean: number; rms_max: number };
  pitch: { min_hz: number | null; max_hz: number | null; mean_hz: number | null };
};

type WordPronunciation = { word: string; score: number | null; reason: string | null };

type PronunciationResult = { overall_score: number | null; words: WordPronunciation[] };

type PhonemeTimestamp = { start: number | null; end: number | null };

type PhonemeAlignmentItem = {
  expected_index: number | null;
  actual_index: number | null;
  expected: string | null;
  actual: string | null;
  status: "match" | "substitution" | "deletion" | "insertion";
  expected_timestamp: PhonemeTimestamp | null;
  actual_timestamp: PhonemeTimestamp | null;
};

type PhonemeAlignmentResult = {
  reference: { phonemes: string[]; duration: number };
  user: { phonemes: string[]; duration: number };
  score: number;
  statistics: {
    reference: number;
    user: number;
    match: number;
    substitution: number;
    deletion: number;
    insertion: number;
  };
  alignment: PhonemeAlignmentItem[];
};

type PronunciationAnalysisItem = PhonemeAlignmentItem & {
  evidence_status: string | null;
  confidence_level: string | null;
  likely_error: boolean;
  evidence_reason: string | null;
  phonetic_similarity: number | null;
  phonetic_distance: number | null;
  error_type: string | null;
  severity: "mild" | "moderate" | "severe" | "uncertain" | null;
  severity_score: number | null;
  severity_reason: string | null;
  phoneme_score: number | null;
  l1_tip: string | null;
};

type WordBreakdownIssue = {
  expected: string | null;
  actual: string | null;
  status: string | null;
  phoneme_score: number | null;
  severity: string | null;
  evidence_status: string | null;
  evidence_reason: string | null;
  l1_tip: string | null;
};

type WordBreakdownItem = {
  word_index: number;
  word: string;
  score: number | null;
  status: "good" | "needs_work" | "error" | "unscored";
  phoneme_count: number;
  issue_count: number;
  issues: WordBreakdownIssue[];
  dictionary_coverage: boolean;
};

type PronunciationAnalysisV2 = {
  items: PronunciationAnalysisItem[];
  word_breakdown?: WordBreakdownItem[];
  summary: {
    total: number;
    matches: number;
    substitutions: number;
    deletions: number;
    insertions: number;
    phoneme_accuracy: number;
    pronunciation_score: number;
    confirmed_matches: number;
    possible_errors: number;
    uncertain: number;
    likely_errors: number;
    mild: number;
    moderate: number;
    severe: number;
    average_severity_score: number;
  };
};

type StressSyllableMeasurement = {
  item_index: number;
  phoneme: string | null;
  duration: number;
  energy: number;
  pitch_hz: number | null;
};

type StressAnalysisItem = {
  word_index: number;
  word: string;
  canonical_syllable_count: number;
  canonical_stress_syllable: number;
  scored: boolean;
  reason?: string;
  index_reliable?: boolean;
  detected_stress_syllable?: number;
  stress_match?: boolean | null;
  syllables?: StressSyllableMeasurement[];
};

type ShadowingAnalysisResult = {
  expected_text: string;
  transcribed_text: string;
  matching: MatchingResult;
  audio: AudioAnalysis;
  pronunciation: PronunciationResult | null;
  phoneme_alignment: PhonemeAlignmentResult | null;
  pronunciation_analysis_v2: PronunciationAnalysisV2 | null;
  stress_analysis: StressAnalysisItem[] | null;
  debug_audio?: {
    user_wav_base64: string | null;
    reference_wav_base64: string | null;
  };
};

// =========================================================
// Helpers
// =========================================================

function downloadJSON(data: unknown, filename: string) {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function downloadBase64Wav(base64: string, filename: string) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
  const blob = new Blob([bytes], { type: "audio/wav" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}

function buildFileName(sentence: string, ext = "json") {
  const cleaned = sentence.replace(/[.,!?;:'"]/g, "");
  const slug = cleaned.trim().toLowerCase().replace(/\s+/g, "_") || "recording";
  const now = new Date();
  const pad = (n: number) => String(n).padStart(2, "0");
  const timestamp =
    `${now.getFullYear()}${pad(now.getMonth() + 1)}${pad(now.getDate())}` +
    `_${pad(now.getHours())}${pad(now.getMinutes())}${pad(now.getSeconds())}`;
  return `${slug}_${timestamp}.${ext}`;
}

function splitWordIntoPhonemeChunks(word: string, phonemeCount: number): string[] {
  const chars = Array.from(word);
  if (phonemeCount <= 0) return [word];
  if (phonemeCount >= chars.length) {
    return chars.map((c) => c).concat(Array(phonemeCount - chars.length).fill(""));
  }
  const chunks: string[] = [];
  const ratio = chars.length / phonemeCount;
  let idx = 0;
  for (let i = 0; i < phonemeCount; i++) {
    const end = Math.round((i + 1) * ratio);
    chunks.push(chars.slice(idx, end).join(""));
    idx = end;
  }
  return chunks;
}

function scoreColor(score: number | null): string {
  if (score === null) return "var(--md-sys-color-outline)";
  if (score >= 85) return "var(--md-custom-match)";
  if (score >= 60) return "var(--md-custom-warning)";
  return "var(--md-custom-error)";
}

// =========================================================
// Main Component
// =========================================================

export const VoiceRecorder: React.FC = () => {
  const { id } = useParams<{ id: string }>();
  const navigate = useNavigate();

  const [courseTitle, setCourseTitle] = useState<string>("");
  const [videoFile, setVideoFile] = useState<File | null>(null);
  const [videoUrl, setVideoUrl] = useState<string | null>(null);
  const [subtitles, setSubtitles] = useState<SubtitleItem[]>([]);
  const [currentIndex, setCurrentIndex] = useState<number>(0);
  const videoRef = useRef<HTMLVideoElement | null>(null);

  useEffect(() => {
    if (id && COURSES_DATA[id]) {
      const course = COURSES_DATA[id];
      setCourseTitle(course.title);
      setVideoUrl(course.videoUrl);
      setSubtitles(course.subtitles);
      setCurrentIndex(0);
    }
  }, [id]);

  const currentSub: SubtitleItem =
    subtitles[currentIndex] || { id: 0, text: "Yes, you can.", startTime: 0, endTime: 1.5 };

  const handleVideoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setVideoFile(file);
    setVideoUrl(URL.createObjectURL(file));
    setResult(null);

    try {
      const formData = new FormData();
      formData.append("file", file);
      const res = await fetch(`${API_BASE_URL}/api/subtitles/extract`, {
        method: "POST",
        body: formData,
      });
      if (res.ok) {
        const data = await res.json();
        if (data.srt_content) {
          const parsed = parseSRT(data.srt_content);
          if (parsed.length > 0) {
            setSubtitles(parsed);
            setCurrentIndex(0);
          }
        }
      }
    } catch (err) {
      console.warn("No embedded subtitles found or extraction skipped:", err);
    }
  };

  const handleSrtUpload = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = (event) => {
      const text = event.target?.result as string;
      const parsed = parseSRT(text);
      if (parsed.length > 0) {
        setSubtitles(parsed);
        setCurrentIndex(0);
      } else {
        alert("This SRT file is invalid or contains no content.");
      }
    };
    reader.readAsText(file);
  };

  useEffect(() => {
    const video = videoRef.current;
    if (!video || subtitles.length === 0) return;
    const handleTimeUpdate = () => {
      if (video.currentTime >= currentSub.endTime) video.pause();
    };
    video.addEventListener("timeupdate", handleTimeUpdate);
    return () => video.removeEventListener("timeupdate", handleTimeUpdate);
  }, [currentSub, subtitles]);

  const playCurrentSegment = () => {
    if (videoRef.current) {
      videoRef.current.currentTime = currentSub.startTime;
      videoRef.current.play();
    }
  };

  const handleNextSentence = () => {
    if (currentIndex < subtitles.length - 1) {
      const nextIdx = currentIndex + 1;
      setCurrentIndex(nextIdx);
      setResult(null);
      if (videoRef.current) {
        videoRef.current.currentTime = subtitles[nextIdx].startTime;
        videoRef.current.play();
      }
    }
  };

  const handlePrevSentence = () => {
    if (currentIndex > 0) {
      const prevIdx = currentIndex - 1;
      setCurrentIndex(prevIdx);
      setResult(null);
      if (videoRef.current) {
        videoRef.current.currentTime = subtitles[prevIdx].startTime;
        videoRef.current.play();
      }
    }
  };

  // Recording State & Audio Analysis
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const isCancelledRef = useRef(false);
  const streamRef = useRef<MediaStream | null>(null);

  const [isRecording, setIsRecording] = useState(false);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);
  const audioRef = useRef<HTMLAudioElement | null>(null);

  const [listenBeforeAnalyze, setListenBeforeAnalyze] = useState<boolean>(() => {
    try {
      const stored = localStorage.getItem("listenBeforeAnalyze");
      return stored === null ? true : stored === "true";
    } catch {
      return true;
    }
  });

  useEffect(() => {
    try {
      localStorage.setItem("listenBeforeAnalyze", String(listenBeforeAnalyze));
    } catch {
      // ignore
    }
  }, [listenBeforeAnalyze]);

  const [pendingRecording, setPendingRecording] = useState<Blob | null>(null);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [result, setResult] = useState<ShadowingAnalysisResult | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const startRecording = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      streamRef.current = stream;

      const mediaRecorder = new MediaRecorder(stream);
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      setAudioUrl(null);
      setResult(null);
      setErrorMessage(null);
      setPendingRecording(null);

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) audioChunksRef.current.push(event.data);
      };

      mediaRecorder.onstop = async () => {
        stream.getTracks().forEach((track) => track.stop());
        streamRef.current = null;

        if (isCancelledRef.current) {
          isCancelledRef.current = false;
          audioChunksRef.current = [];
          setAudioUrl(null);
          return;
        }

        const audioBlob = new Blob(audioChunksRef.current, { type: mediaRecorder.mimeType });
        const url = URL.createObjectURL(audioBlob);
        setAudioUrl(url);

        if (listenBeforeAnalyze) {
          setPendingRecording(audioBlob);
        } else {
          await analyzeShadowing(audioBlob);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (error) {
      console.error("Microphone access failed:", error);
      alert("Could not access the microphone.");
    }
  };

  const stopRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;
    isCancelledRef.current = false;
    if (recorder.state === "recording") recorder.stop();
    setIsRecording(false);
  };

  const cancelRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;
    isCancelledRef.current = true;
    if (recorder.state === "recording") recorder.stop();
    setIsRecording(false);
  };

  const confirmPendingRecording = async () => {
    if (!pendingRecording) return;
    const blob = pendingRecording;
    setPendingRecording(null);
    await analyzeShadowing(blob);
  };

  const reRecordFromPending = () => {
    setPendingRecording(null);
    setAudioUrl(null);
    startRecording();
  };

  const analyzeShadowing = async (audioBlob: Blob) => {
    setIsAnalyzing(true);
    setErrorMessage(null);
    try {
      const formData = new FormData();
      const mimeType = audioBlob.type || "audio/webm";
      formData.append("audio", new Blob([audioBlob], { type: mimeType }), "recording.webm");
      formData.append("expected_text", currentSub.text);

      if (videoFile) {
        try {
          const refAudioBlob = await extractAudioClip(
            videoFile,
            currentSub.startTime,
            currentSub.endTime,
            0.3
          );
          formData.append("reference_audio", refAudioBlob, "reference.wav");
          formData.append("reference_anchor_start", String(Math.min(0.3, currentSub.startTime)));
          formData.append(
            "reference_anchor_end",
            String(currentSub.endTime - currentSub.startTime + Math.min(0.3, currentSub.startTime))
          );
        } catch (clipErr) {
          console.warn("Could not extract reference audio clip:", clipErr);
        }
      }

      const response = await fetch(`${API_BASE_URL}/api/shadowing/analyze`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Server returned ${response.status}: ${errorText}`);
      }

      const data: ShadowingAnalysisResult = await response.json();
      setResult(data);
    } catch (err) {
      console.error("Error analyzing audio:", err);
      setErrorMessage("Something went wrong sending or analyzing your audio. Please try again.");
    } finally {
      setIsAnalyzing(false);
    }
  };

  // Reference Audio Playback
  const [decodedReferenceBuffer, setDecodedReferenceBuffer] = useState<AudioBuffer | null>(null);
  const playbackAudioContextRef = useRef<AudioContext | null>(null);

  useEffect(() => {
    const base64 = result?.debug_audio?.reference_wav_base64;
    if (!base64) {
      setDecodedReferenceBuffer(null);
      return;
    }
    const ctx =
      playbackAudioContextRef.current ??
      new (window.AudioContext || (window as any).webkitAudioContext)();
    playbackAudioContextRef.current = ctx;

    try {
      const binary = atob(base64);
      const bytes = new Uint8Array(binary.length);
      for (let i = 0; i < binary.length; i++) bytes[i] = binary.charCodeAt(i);
      ctx
        .decodeAudioData(bytes.buffer.slice(0))
        .then((buffer) => setDecodedReferenceBuffer(buffer))
        .catch((error) => {
          console.error("Could not decode reference audio for playback:", error);
          setDecodedReferenceBuffer(null);
        });
    } catch (error) {
      console.error("Could not decode reference audio base64:", error);
      setDecodedReferenceBuffer(null);
    }
  }, [result?.debug_audio?.reference_wav_base64]);

  const playReferenceSnippet = (start: number | null, end: number | null) => {
    const ctx = playbackAudioContextRef.current;
    const buffer = decodedReferenceBuffer;
    if (!ctx || !buffer || start === null || end === null) return;
    if (ctx.state === "suspended") ctx.resume();
    const source = ctx.createBufferSource();
    source.buffer = buffer;
    source.connect(ctx.destination);
    source.start(0, Math.max(0, start), Math.max(0.03, end - start));
  };

  // Tooltip Portal State
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [tooltip, setTooltip] = useState<{
    content: React.ReactNode;
    anchor: { top: number; bottom: number; centerX: number };
  } | null>(null);
  const [tooltipPos, setTooltipPos] = useState<{
    x: number;
    y: number;
    placement: "top" | "bottom";
    arrowX: number;
  } | null>(null);
  const hideTooltipTimeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [activeTooltipKey, setActiveTooltipKey] = useState<string | null>(null);

  const cancelHideTooltip = () => {
    if (hideTooltipTimeoutRef.current) {
      clearTimeout(hideTooltipTimeoutRef.current);
      hideTooltipTimeoutRef.current = null;
    }
  };
  useEffect(() => cancelHideTooltip, []);

  const showTooltip = (e: React.MouseEvent<HTMLElement>, content: React.ReactNode) => {
    cancelHideTooltip();
    const rect = e.currentTarget.getBoundingClientRect();
    setTooltipPos(null);
    setTooltip({
      content,
      anchor: { top: rect.top, bottom: rect.bottom, centerX: rect.left + rect.width / 2 },
    });
  };

  const hideTooltip = () => {
    cancelHideTooltip();
    hideTooltipTimeoutRef.current = setTimeout(() => {
      setTooltip(null);
      setTooltipPos(null);
      setActiveTooltipKey(null);
    }, 200);
  };

  const toggleTooltip = (e: React.MouseEvent<HTMLElement>, content: React.ReactNode, key: string) => {
    cancelHideTooltip();
    if (activeTooltipKey === key) {
      setTooltip(null);
      setTooltipPos(null);
      setActiveTooltipKey(null);
      return;
    }
    showTooltip(e, content);
    setActiveTooltipKey(key);
  };

  useEffect(() => {
    if (!tooltip) return;
    const handleOutsideClick = (e: MouseEvent) => {
      const target = e.target as HTMLElement;
      if (tooltipRef.current?.contains(target) || target.closest(".problematic-letter")) return;
      setTooltip(null);
      setTooltipPos(null);
      setActiveTooltipKey(null);
    };
    document.addEventListener("click", handleOutsideClick);
    return () => document.removeEventListener("click", handleOutsideClick);
  }, [tooltip]);

  useLayoutEffect(() => {
    if (!tooltip || !tooltipRef.current) return;
    const el = tooltipRef.current;
    const rect = el.getBoundingClientRect();
    const { anchor } = tooltip;
    const padding = 12;
    const gap = 10;
    const vw = window.innerWidth;
    const halfW = rect.width / 2;
    let x = anchor.centerX;
    if (x - halfW < padding) x = halfW + padding;
    if (x + halfW > vw - padding) x = vw - halfW - padding;
    let placement: "top" | "bottom" = "top";
    let y = anchor.top - gap;
    if (anchor.top - rect.height - gap < padding) {
      placement = "bottom";
      y = anchor.bottom + gap;
    }
    const tooltipLeft = x - halfW;
    const rawArrowX = anchor.centerX - tooltipLeft;
    const arrowX = Math.max(12, Math.min(rect.width - 12, rawArrowX));
    setTooltipPos({ x, y, placement, arrowX });
  }, [tooltip]);

  // Derived Values
  const v2 = result?.pronunciation_analysis_v2 ?? null;
  const wordBreakdown = v2?.word_breakdown ?? [];
  const alignment = result?.phoneme_alignment?.alignment ?? [];
  const overallScore = v2?.summary?.pronunciation_score ?? result?.matching?.accuracy ?? 0;

  const [activeTab, setActiveTab] = useState<"overview" | "pronunciation" | "phonemes">("overview");

  // Deduplicated L1 tips direct from backend
  const l1TipCards = useMemo(() => {
    if (!v2?.items) return [];
    const seen = new Set<string>();
    const cards: { pair: string; tip: string }[] = [];
    for (const item of v2.items) {
      if (item.l1_tip && !seen.has(item.l1_tip)) {
        seen.add(item.l1_tip);
        cards.push({
          pair:
            item.status === "substitution"
              ? `/${item.expected}/ → /${item.actual}/`
              : `/${item.expected}/`,
          tip: item.l1_tip,
        });
      }
    }
    return cards;
  }, [v2]);

  const buildSentenceView = (
    wordBreakdownData: WordBreakdownItem[],
    alignmentData: PhonemeAlignmentItem[]
  ) => {
    let offset = 0;
    return (
      <Box className="sentence-view">
        <Typography className="sentence-view-label">Word-by-Word Phonetic Breakdown</Typography>
        <div className="sentence-flow">
          {wordBreakdownData.map((w) => {
            const wordPhonemes = alignmentData.slice(offset, offset + w.phoneme_count);
            offset += w.phoneme_count;
            const chunks = splitWordIntoPhonemeChunks(w.word, w.phoneme_count);

            return (
              <span key={w.word_index} className="word-text">
                {chunks.map((chunk, i) => {
                  const phoneme = wordPhonemes[i];
                  const isProblem = phoneme && phoneme.status !== "match";
                  if (!isProblem || !chunk) return <span key={i}>{chunk}</span>;

                  const issue = w.issues.find((iss) => iss.expected === phoneme.expected);

                  const tooltipContent = (
                    <>
                      <div className="tooltip-phoneme-compare">
                        <span className="tooltip-phoneme-expected">{phoneme.expected}</span>
                        {phoneme.status === "substitution" && (
                          <>
                            <span className="tooltip-arrow">→</span>
                            <span className="tooltip-phoneme-actual">{phoneme.actual}</span>
                          </>
                        )}
                        {phoneme.status === "deletion" && (
                          <span className="tooltip-phoneme-missing">omitted</span>
                        )}
                        {phoneme.status === "insertion" && (
                          <span className="tooltip-phoneme-actual">+ {phoneme.actual}</span>
                        )}
                        {issue?.phoneme_score != null && (
                          <span className="tooltip-score">{Math.round(issue.phoneme_score)}%</span>
                        )}
                      </div>

                      {issue?.evidence_reason && <p className="tooltip-reason">{issue.evidence_reason}</p>}
                      {issue?.l1_tip && <p className="tooltip-tip">💡 {issue.l1_tip}</p>}

                      {phoneme.status !== "insertion" &&
                        phoneme.expected_timestamp &&
                        decodedReferenceBuffer && (
                          <button
                            className="tooltip-play-btn"
                            onClick={(e) => {
                              e.stopPropagation();
                              playReferenceSnippet(
                                phoneme.expected_timestamp!.start,
                                phoneme.expected_timestamp!.end
                              );
                            }}
                          >
                            🔊 Hear correct pronunciation
                          </button>
                        )}
                    </>
                  );

                  const tooltipKey = `${w.word_index}-${i}`;

                  return (
                    <span
                      key={i}
                      className={`problematic-letter ${issue?.severity ?? ""}`}
                      onMouseEnter={(e) => showTooltip(e, tooltipContent)}
                      onMouseLeave={hideTooltip}
                      onClick={(e) => {
                        e.stopPropagation();
                        toggleTooltip(e, tooltipContent, tooltipKey);
                      }}
                    >
                      {chunk}
                    </span>
                  );
                })}
              </span>
            );
          })}
        </div>

        {tooltip &&
          createPortal(
            <div
              ref={tooltipRef}
              className={`phoneme-tooltip-portal ${tooltipPos?.placement ?? "top"}`}
              style={
                {
                  left: tooltipPos?.x ?? 0,
                  top: tooltipPos?.y ?? 0,
                  visibility: tooltipPos ? "visible" : "hidden",
                  "--arrow-x": `${tooltipPos?.arrowX ?? 0}px`,
                } as React.CSSProperties
              }
              onMouseEnter={cancelHideTooltip}
              onMouseLeave={hideTooltip}
            >
              {tooltip.content}
            </div>,
            document.body
          )}
      </Box>
    );
  };

  return (
    <Box dir="ltr" sx={{ maxWidth: 1000, mx: "auto", display: "flex", flexDirection: "column", gap: 3, pb: 6 }}>
      {/* Top Bar Navigation */}
      <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <Button
          variant="outlined"
          startIcon={<ArrowBackRoundedIcon />}
          onClick={() => navigate("/library")}
          sx={{ borderRadius: "var(--md-sys-shape-corner-full)", textTransform: "none" }}
        >
          Back to Library
        </Button>
        {courseTitle && (
          <Typography variant="title-large" sx={{ fontWeight: 700, color: "var(--md-sys-color-on-surface)" }}>
            {courseTitle}
          </Typography>
        )}
      </Box>

      {errorMessage && (
        <Alert severity="error" onClose={() => setErrorMessage(null)} sx={{ borderRadius: "var(--md-sys-shape-corner-medium)" }}>
          {errorMessage}
        </Alert>
      )}

      {/* Media Source Actions (Upload Bar) */}
      <Paper
        elevation={0}
        sx={{
          p: 2,
          borderRadius: "var(--md-sys-shape-corner-large)",
          backgroundColor: "var(--md-sys-color-surface-container-low)",
          border: "1px solid var(--md-sys-color-outline-variant)",
          display: "flex",
          gap: 2,
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <Button
          variant="outlined"
          component="label"
          startIcon={<MovieRoundedIcon />}
          sx={{ borderRadius: "var(--md-sys-shape-corner-full)", textTransform: "none" }}
        >
          {videoFile ? videoFile.name : "Upload Video"}
          <input type="file" accept="video/*" hidden onChange={handleVideoUpload} />
        </Button>

        <Button
          variant="outlined"
          component="label"
          startIcon={<SubtitlesRoundedIcon />}
          sx={{ borderRadius: "var(--md-sys-shape-corner-full)", textTransform: "none" }}
        >
          {subtitles.length > 0 ? `${subtitles.length} sentences loaded` : "Upload SRT File"}
          <input type="file" accept=".srt" hidden onChange={handleSrtUpload} />
        </Button>
      </Paper>

      {/* Video Player & Sentence Target Card */}
      <Paper
        elevation={0}
        sx={{
          p: 3,
          borderRadius: "var(--md-sys-shape-corner-extra-large)",
          backgroundColor: "var(--md-sys-color-surface-container-low)",
          border: "1px solid var(--md-sys-color-outline-variant)",
          display: "flex",
          flexDirection: "column",
          gap: 2.5,
        }}
      >
        {videoUrl && (
          <Box
            sx={{
              width: "100%",
              maxHeight: 380,
              backgroundColor: "#000",
              borderRadius: "var(--md-sys-shape-corner-large)",
              overflow: "hidden",
              display: "flex",
              justifyContent: "center",
            }}
          >
            <video ref={videoRef} src={videoUrl} controls style={{ width: "100%", maxHeight: "380px" }} />
          </Box>
        )}

        <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <Chip
            label={subtitles.length > 0 ? `Sentence ${currentIndex + 1} of ${subtitles.length}` : "Sample sentence"}
            size="small"
            sx={{
              backgroundColor: "var(--md-sys-color-primary-container)",
              color: "var(--md-sys-color-on-primary-container)",
              fontWeight: 700,
            }}
          />
          <Stack direction="row" spacing={1}>
            <MuiTooltip title="Replay sentence">
              <IconButton size="small" onClick={playCurrentSegment} sx={{ minWidth: 40, minHeight: 40 }}>
                <Replay10RoundedIcon />
              </IconButton>
            </MuiTooltip>
            <MuiTooltip title="Previous sentence">
              <IconButton
                size="small"
                onClick={handlePrevSentence}
                disabled={currentIndex === 0}
                sx={{ minWidth: 40, minHeight: 40 }}
              >
                <SkipPreviousRoundedIcon />
              </IconButton>
            </MuiTooltip>
            <MuiTooltip title="Next sentence">
              <IconButton
                size="small"
                onClick={handleNextSentence}
                disabled={currentIndex >= subtitles.length - 1}
                sx={{ minWidth: 40, minHeight: 40 }}
              >
                <SkipNextRoundedIcon />
              </IconButton>
            </MuiTooltip>
          </Stack>
        </Box>

        {/* Target Sentence Display Container */}
        <Box
          sx={{
            py: 3.5,
            px: 4,
            borderRadius: "var(--md-sys-shape-corner-large)",
            backgroundColor: "var(--md-sys-color-surface-container)",
            border: "1px solid var(--md-sys-color-outline-variant)",
            textAlign: "center",
          }}
        >
          <Typography
            variant="h4"
            sx={{
              fontWeight: 700,
              letterSpacing: 0.5,
              color: "var(--md-sys-color-on-surface)",
              fontFamily: "Roboto, sans-serif",
            }}
          >
            "{currentSub.text}"
          </Typography>
        </Box>
      </Paper>

      {/* Recording Control & Options Action Bar */}
      <Paper
        elevation={0}
        sx={{
          p: 2.5,
          borderRadius: "var(--md-sys-shape-corner-large)",
          backgroundColor: "var(--md-sys-color-surface-container-low)",
          border: "1px solid var(--md-sys-color-outline-variant)",
          display: "flex",
          flexDirection: "column",
          gap: 2,
        }}
      >
        <FormControlLabel
          control={
            <Switch
              checked={listenBeforeAnalyze}
              onChange={(e) => setListenBeforeAnalyze(e.target.checked)}
              color="primary"
            />
          }
          label="Play back my recording before sending it for analysis"
          sx={{ color: "var(--md-sys-color-on-surface-variant)" }}
        />

        <Box sx={{ display: "flex", alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", gap: 2 }}>
          {pendingRecording ? (
            <Stack direction="row" spacing={1.5}>
              <Button
                variant="contained"
                startIcon={<CheckRoundedIcon />}
                onClick={confirmPendingRecording}
                disabled={isAnalyzing}
                sx={{
                  borderRadius: "var(--md-sys-shape-corner-full)",
                  backgroundColor: "var(--md-sys-color-primary)",
                  color: "var(--md-sys-color-on-primary)",
                  textTransform: "none",
                  fontWeight: 700,
                  px: 3,
                }}
              >
                Confirm & Analyze
              </Button>
              <Button
                variant="outlined"
                startIcon={<ReplayRoundedIcon />}
                onClick={reRecordFromPending}
                sx={{ borderRadius: "var(--md-sys-shape-corner-full)", textTransform: "none" }}
              >
                Re-record
              </Button>
            </Stack>
          ) : !isRecording ? (
            <Button
              variant="contained"
              startIcon={<MicRoundedIcon />}
              onClick={startRecording}
              disabled={isAnalyzing}
              sx={{
                borderRadius: "var(--md-sys-shape-corner-full)",
                backgroundColor: "var(--md-sys-color-primary)",
                color: "var(--md-sys-color-on-primary)",
                px: 3.5,
                py: 1.2,
                fontWeight: 700,
                textTransform: "none",
              }}
            >
              Start Recording
            </Button>
          ) : (
            <Stack direction="row" spacing={1.5}>
              <Button
                variant="contained"
                startIcon={<StopRoundedIcon />}
                onClick={stopRecording}
                sx={{
                  borderRadius: "var(--md-sys-shape-corner-full)",
                  backgroundColor: "var(--md-sys-color-error)",
                  color: "var(--md-sys-color-on-error)",
                  textTransform: "none",
                  fontWeight: 700,
                  px: 3,
                }}
              >
                Stop Recording
              </Button>
              <Button
                variant="outlined"
                startIcon={<CloseRoundedIcon />}
                onClick={cancelRecording}
                sx={{ borderRadius: "var(--md-sys-shape-corner-full)", textTransform: "none" }}
              >
                Cancel
              </Button>
            </Stack>
          )}

          {audioUrl && (
            <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <VolumeUpRoundedIcon sx={{ color: "var(--md-sys-color-on-surface-variant)" }} />
              <audio
                ref={audioRef}
                controls
                src={audioUrl}
                onLoadedMetadata={(e) => {
                  e.currentTarget.volume = 0.5;
                }}
              />
            </Box>
          )}
        </Box>
      </Paper>

      {/* Processing Loader Indicator */}
      {isAnalyzing && (
        <Paper
          elevation={0}
          sx={{
            p: 4,
            textAlign: "center",
            borderRadius: "var(--md-sys-shape-corner-large)",
            backgroundColor: "var(--md-sys-color-surface-container-low)",
            border: "1px solid var(--md-sys-color-outline-variant)",
          }}
        >
          <CircularProgress size={40} sx={{ color: "var(--md-sys-color-primary)", mb: 2 }} />
          <Typography variant="body1" sx={{ color: "var(--md-sys-color-on-surface)" }}>
            Extracting reference audio and analyzing pronunciation…
          </Typography>
        </Paper>
      )}

      {/* Complete Dashboard Results Container */}
      {result && !isAnalyzing && (
        <Paper
          elevation={0}
          sx={{
            p: 3,
            borderRadius: "var(--md-sys-shape-corner-extra-large)",
            backgroundColor: "var(--md-sys-color-surface-container-low)",
            border: "1px solid var(--md-sys-color-outline-variant)",
            display: "flex",
            flexDirection: "column",
            gap: 3,
          }}
        >
          {/* Header Score & M3 Segmented Navigation Bar */}
          <Box sx={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 2 }}>
            <Box sx={{ display: "flex", alignItems: "center", gap: 2 }}>
              <Box
                sx={{
                  width: 64,
                  height: 64,
                  borderRadius: "var(--md-sys-shape-corner-full)",
                  backgroundColor: scoreColor(overallScore),
                  color: "#141218",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 800,
                  fontSize: "20px",
                }}
              >
                {Math.round(overallScore)}%
              </Box>
              <Box>
                <Typography variant="h6" sx={{ fontWeight: 700 }}>
                  {v2 ? "Final Phonetic Analysis" : "Word Matching (No Reference Audio)"}
                </Typography>
                <Typography variant="body2" sx={{ color: "var(--md-sys-color-on-surface-variant)" }}>
                  {v2
                    ? `Phoneme accuracy: ${v2.summary.phoneme_accuracy}%`
                    : `Word accuracy: ${result.matching.accuracy}%`}
                </Typography>
              </Box>
            </Box>

            <Stack direction="row" spacing={1.5} alignItems="center">
              <ToggleButtonGroup
                value={activeTab}
                exclusive
                onChange={(_, val) => val && setActiveTab(val)}
                size="small"
                sx={{
                  backgroundColor: "var(--md-sys-color-surface-container)",
                  borderRadius: "var(--md-sys-shape-corner-full)",
                  p: "4px",
                  "& .MuiToggleButton-root": {
                    border: "none",
                    borderRadius: "var(--md-sys-shape-corner-full)",
                    px: 2,
                    py: 0.75,
                    color: "var(--md-sys-color-on-surface-variant)",
                    textTransform: "none",
                    "&.Mui-selected": {
                      backgroundColor: "var(--md-sys-color-secondary-container)",
                      color: "var(--md-sys-color-on-secondary-container)",
                      fontWeight: 700,
                    },
                  },
                }}
              >
                <ToggleButton value="overview">Words & Score</ToggleButton>
                <ToggleButton value="pronunciation">Audio Features</ToggleButton>
                <ToggleButton value="phonemes" disabled={!v2}>
                  Phoneme Analysis
                </ToggleButton>
              </ToggleButtonGroup>

              <MuiTooltip title="Download full JSON + audio files">
                <IconButton
                  size="small"
                  onClick={() => {
                    downloadJSON(
                      {
                        "Words & Score": {
                          expected_text: result.expected_text,
                          transcribed_text: result.transcribed_text,
                          matching: result.matching,
                        },
                        "Acoustic & Pitch": {
                          pronunciation: result.pronunciation,
                          audio: result.audio,
                        },
                        "Pronunciation Analysis": {
                          pronunciation_analysis_v2: result.pronunciation_analysis_v2,
                          phoneme_alignment: result.phoneme_alignment,
                          stress_analysis: result.stress_analysis,
                        },
                      },
                      buildFileName(result.expected_text)
                    );
                    if (result.debug_audio?.user_wav_base64) {
                      downloadBase64Wav(
                        result.debug_audio.user_wav_base64,
                        buildFileName(result.expected_text + " user", "wav")
                      );
                    }
                    if (result.debug_audio?.reference_wav_base64) {
                      downloadBase64Wav(
                        result.debug_audio.reference_wav_base64,
                        buildFileName(result.expected_text + " reference", "wav")
                      );
                    }
                  }}
                  sx={{
                    backgroundColor: "var(--md-sys-color-surface-container)",
                    color: "var(--md-sys-color-on-surface)",
                    minWidth: 40,
                    minHeight: 40,
                  }}
                >
                  <DownloadRoundedIcon fontSize="small" />
                </IconButton>
              </MuiTooltip>
            </Stack>
          </Box>

          <Divider sx={{ borderColor: "var(--md-sys-color-outline-variant)" }} />

          {/* TAB 1: Words & Overall Score */}
          {activeTab === "overview" && (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                {result.matching.matches.map((match, index) => (
                  <Chip
                    key={index}
                    label={
                      match.status === "correct"
                        ? match.expected.join(" ")
                        : match.status === "missing"
                        ? `${match.expected.join(" ")} (omitted)`
                        : match.status === "replaced"
                        ? `${match.expected.join(" ")} → ${match.actual.join(" ")}`
                        : `+ ${match.actual.join(" ")}`
                    }
                    sx={{
                      borderRadius: "var(--md-sys-shape-corner-medium)",
                      backgroundColor:
                        match.status === "correct"
                          ? "var(--md-custom-match-container)"
                          : "var(--md-custom-warning-container)",
                      color:
                        match.status === "correct"
                          ? "var(--md-custom-on-match-container)"
                          : "var(--md-custom-on-warning-container)",
                      fontWeight: 600,
                    }}
                  />
                ))}
              </Box>
              {result.transcribed_text && (
                <Typography variant="body2" sx={{ color: "var(--md-sys-color-on-surface-variant)" }}>
                  Heard text: "{result.transcribed_text}"
                </Typography>
              )}
            </Box>
          )}

          {/* TAB 2: Acoustic & Pitch Metrics */}
          {activeTab === "pronunciation" && (
            <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" }, gap: 2 }}>
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  borderRadius: "var(--md-sys-shape-corner-medium)",
                  backgroundColor: "var(--md-sys-color-surface-container)",
                }}
              >
                <Typography variant="caption" sx={{ color: "var(--md-sys-color-on-surface-variant)" }}>Speech Duration</Typography>
                <Typography variant="h6">{result.audio.speech?.duration}s</Typography>
              </Paper>
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  borderRadius: "var(--md-sys-shape-corner-medium)",
                  backgroundColor: "var(--md-sys-color-surface-container)",
                }}
              >
                <Typography variant="caption" sx={{ color: "var(--md-sys-color-on-surface-variant)" }}>Average Pitch</Typography>
                <Typography variant="h6">
                  {result.audio.pitch?.mean_hz !== null ? `${result.audio.pitch.mean_hz} Hz` : "—"}
                </Typography>
              </Paper>
              <Paper
                elevation={0}
                sx={{
                  p: 2,
                  borderRadius: "var(--md-sys-shape-corner-medium)",
                  backgroundColor: "var(--md-sys-color-surface-container)",
                }}
              >
                <Typography variant="caption" sx={{ color: "var(--md-sys-color-on-surface-variant)" }}>RMS Energy</Typography>
                <Typography variant="h6">{result.audio.energy?.rms_mean}</Typography>
              </Paper>
            </Box>
          )}

          {/* TAB 3: Detailed Phoneme & L1 Analysis */}
          {activeTab === "phonemes" && v2 && (
            <Box sx={{ display: "flex", flexDirection: "column", gap: 3 }}>
              {/* Summary Badges */}
              <Box sx={{ display: "flex", gap: 1, flexWrap: "wrap" }}>
                <Chip
                  label={`${v2.summary.confirmed_matches} Confirmed`}
                  sx={{ backgroundColor: "var(--md-custom-match-container)", color: "var(--md-custom-on-match-container)", fontWeight: 600 }}
                />
                <Chip
                  label={`${v2.summary.possible_errors} Possible`}
                  sx={{ backgroundColor: "var(--md-custom-warning-container)", color: "var(--md-custom-on-warning-container)", fontWeight: 600 }}
                />
                <Chip
                  label={`${v2.summary.likely_errors} Likely Errors`}
                  sx={{ backgroundColor: "var(--md-custom-error-container)", color: "var(--md-custom-on-error-container)", fontWeight: 600 }}
                />
                <Chip
                  label={`${v2.summary.uncertain} Uncertain`}
                  sx={{ backgroundColor: "var(--md-sys-color-surface-container-highest)", color: "var(--md-sys-color-on-surface-variant)", fontWeight: 600 }}
                />
              </Box>

              {/* Interactive Sentence View Breakdown */}
              {wordBreakdown.length > 0 && alignment.length > 0 && buildSentenceView(wordBreakdown, alignment)}

              {/* L1 Coaching Cards Section */}
              {l1TipCards.length > 0 && (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <LightbulbRoundedIcon sx={{ color: "var(--md-sys-color-tertiary)" }} />
                    <Typography variant="h6" sx={{ fontWeight: 700, fontSize: "16px" }}>
                      Pronunciation Tips for Persian (Farsi) Speakers
                    </Typography>
                  </Box>
                  <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" }, gap: 2 }}>
                    {l1TipCards.map((card, idx) => (
                      <Paper
                        key={idx}
                        elevation={0}
                        sx={{
                          p: 2.5,
                          borderRadius: "var(--md-sys-shape-corner-large)",
                          backgroundColor: "var(--md-sys-color-tertiary-container)",
                          color: "var(--md-sys-color-on-tertiary-container)",
                          border: "1px solid var(--md-sys-color-outline-variant)",
                          display: "flex",
                          flexDirection: "column",
                          gap: 1,
                        }}
                      >
                        <Chip
                          label={card.pair}
                          size="small"
                          sx={{
                            alignSelf: "flex-start",
                            backgroundColor: "var(--md-sys-color-surface)",
                            color: "var(--md-sys-color-on-surface)",
                            fontWeight: 700,
                            fontFamily: "monospace",
                          }}
                        />
                        <Typography variant="body2" sx={{ lineHeight: 1.7 }}>
                          {card.tip}
                        </Typography>
                      </Paper>
                    ))}
                  </Box>
                </Box>
              )}

              {/* Syllable Stress Section */}
              {result.stress_analysis && result.stress_analysis.some((s) => s.scored) && (
                <Box sx={{ display: "flex", flexDirection: "column", gap: 2 }}>
                  <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
                    <GraphicEqRoundedIcon sx={{ color: "var(--md-sys-color-primary)" }} />
                    <Typography variant="h6" sx={{ fontWeight: 700, fontSize: "16px" }}>
                      Syllable Stress
                    </Typography>
                  </Box>
                  <Box sx={{ display: "flex", flexWrap: "wrap", gap: 2 }}>
                    {result.stress_analysis
                      .filter((s) => s.scored)
                      .map((s) => (
                        <Box key={s.word_index} className="stress-word">
                          <strong>{s.word}</strong>
                          <div className="stress-word__syllables">
                            {Array.from({ length: s.canonical_syllable_count }).map((_, i) => (
                              <span
                                key={i}
                                className={[
                                  "stress-syllable",
                                  i === s.canonical_stress_syllable ? "canonical-stress" : "",
                                  s.index_reliable && i === s.detected_stress_syllable ? "detected-stress" : "",
                                ]
                                  .filter(Boolean)
                                  .join(" ")}
                              >
                                {i + 1}
                              </span>
                            ))}
                          </div>
                          <Typography variant="caption" sx={{ color: "var(--md-sys-color-on-surface-variant)" }}>
                            {s.stress_match === true
                              ? "✓ Correct stress"
                              : s.stress_match === false
                              ? "Stress differed from expected"
                              : "Not comparable"}
                          </Typography>
                        </Box>
                      ))}
                  </Box>
                </Box>
              )}
            </Box>
          )}
        </Paper>
      )}
    </Box>
  );
};

export default VoiceRecorder;