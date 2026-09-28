export interface SubtitleItem {
  id: number;
  startTime: number; // ثانیه
  endTime: number;   // ثانیه
  text: string;
}

export function parseSRT(srtContent: string): SubtitleItem[] {
  if (!srtContent) return [];

  // ۱. حذف BOM، یکسان‌سازی پایان خط‌ها (\r\n -> \n) و پاک‌سازی فاصله
  const cleanContent = srtContent
    .replace(/^\uFEFF/, "")
    .replace(/\r\n/g, "\n")
    .replace(/\r/g, "\n")
    .trim();

  const blocks = cleanContent.split(/\n\n+/);
  const result: SubtitleItem[] = [];

  const timeToSeconds = (timeStr: string): number => {
    const [times, millis] = timeStr.replace(".", ",").split(",");
    const [hours, minutes, seconds] = times.split(":").map(Number);
    return hours * 3600 + minutes * 60 + seconds + Number(millis) / 1000;
  };

  for (const block of blocks) {
    const lines = block.split("\n").map((l) => l.trim()).filter(Boolean);
    if (lines.length < 2) continue;

    // پیدا کردن خط زمان که حاوی <-- است
    const timeLineIndex = lines[0].includes("-->") ? 0 : 1;
    const timeLine = lines[timeLineIndex];

    if (!timeLine || !timeLine.includes("-->")) continue;

    const timeMatch = timeLine.match(
      /(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})/
    );

    if (!timeMatch) continue;

    const startTime = timeToSeconds(timeMatch[1]);
    const endTime = timeToSeconds(timeMatch[2]);
    const textLines = lines.slice(timeLineIndex + 1);
    const text = textLines.join(" ").replace(/<[^>]*>/g, "").trim();

    if (text) {
      result.push({
        id: result.length + 1,
        startTime,
        endTime,
        text,
      });
    }
  }

  return result;
}