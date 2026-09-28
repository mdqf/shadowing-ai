import "./ScoreRing.css";

type ScoreRingProps = {
  /** 0-100 */
  score: number;
  /** Diameter in px */
  size?: number;
  label?: string;
};

function scoreColor(score: number): string {
  if (score >= 85) return "var(--color-success)";
  if (score >= 60) return "var(--color-warning)";
  return "var(--color-danger)";
}

export default function ScoreRing({
  score,
  size = 88,
  label,
}: ScoreRingProps) {
  const clamped = Math.max(0, Math.min(100, score));
  const strokeWidth = Math.max(4, size * 0.09);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - clamped / 100);
  const color = scoreColor(clamped);

  return (
    <div className="ui-score-ring" style={{ width: size }}>
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(255,255,255,0.08)"
          strokeWidth={strokeWidth}
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          className="ui-score-ring__progress"
        />
        <text
          x="50%"
          y="50%"
          textAnchor="middle"
          dominantBaseline="central"
          className="ui-score-ring__text"
        >
          {Math.round(clamped)}%
        </text>
      </svg>
      {label && <div className="ui-score-ring__label">{label}</div>}
    </div>
  );
}
