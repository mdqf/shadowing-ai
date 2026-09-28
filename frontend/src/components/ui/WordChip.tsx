import type { ReactNode } from "react";
import "./WordChip.css";

type WordChipStatus = "good" | "needs_work" | "error" | "unscored";

type WordChipProps = {
  word: string;
  status: WordChipStatus;
  score?: number | null;
  onClick?: () => void;
  children?: ReactNode;
};

export default function WordChip({
  word,
  status,
  score,
  onClick,
  children,
}: WordChipProps) {
  const className = `ui-word-chip ui-word-chip--${status}`;

  const content = (
    <>
      <span className="ui-word-chip__word">{word}</span>
      {score !== undefined && score !== null && (
        <span className="ui-word-chip__score">{Math.round(score)}%</span>
      )}
      {children}
    </>
  );

  if (onClick) {
    return (
      <button type="button" className={className} onClick={onClick}>
        {content}
      </button>
    );
  }

  return <div className={className}>{content}</div>;
}
