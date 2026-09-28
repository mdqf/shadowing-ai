import { useState, useEffect, useRef } from "react";

interface SubtitleStatusProps {
  isExtractingSubtitles: boolean;
  subtitles: unknown[];
  subtitleTracks: unknown[];
}

type Status = "loading" | "success" | "error" | "hidden";

function SubtitleStatus({
  isExtractingSubtitles,
  subtitles,
  subtitleTracks,
}: SubtitleStatusProps) {
  const [status, setStatus] = useState<Status>("hidden");
  const successTimer = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    if (successTimer.current) clearTimeout(successTimer.current);

    if (isExtractingSubtitles) {
      setStatus("loading");
      return;
    }

    if (subtitles.length > 0) {
      setStatus("success");
      successTimer.current = setTimeout(() => setStatus("hidden"), 2000);
    } else if (subtitleTracks.length > 0) {
      setStatus("error");
    } else {
      setStatus("hidden");
    }

    return () => {
      if (successTimer.current) clearTimeout(successTimer.current);
    };
  }, [isExtractingSubtitles, subtitles.length, subtitleTracks.length]);

  if (status === "hidden") return null;

  return (
    <span className={`extracting-indicator ${status}`} aria-live="polite">
      {status === "loading" && (
        <span className="extracting-spinner" aria-label="Loading" />
      )}
      {status === "success" && (
        <span className="status-icon" aria-label="Loaded">✅</span>
      )}
      {status === "error" && (
        <span className="status-icon" aria-label="Empty">⚠️</span>
      )}
    </span>
  );
}

export default SubtitleStatus;