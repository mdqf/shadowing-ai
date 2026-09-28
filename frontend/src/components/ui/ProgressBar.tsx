import "./ProgressBar.css";

type ProgressBarProps = {
  /** 0-100 */
  value: number;
  label?: string;
};

export default function ProgressBar({ value, label }: ProgressBarProps) {
  const clamped = Math.max(0, Math.min(100, value));

  return (
    <div className="ui-progress-bar">
      {label && (
        <div className="ui-progress-bar__label-row">
          <span>{label}</span>
          <span>{Math.round(clamped)}%</span>
        </div>
      )}
      <div className="ui-progress-bar__track">
        <div
          className="ui-progress-bar__fill"
          style={{ width: `${clamped}%` }}
        />
      </div>
    </div>
  );
}
