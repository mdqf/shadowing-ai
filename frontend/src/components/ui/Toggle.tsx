import "./Toggle.css";

type ToggleProps = {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label?: string;
  disabled?: boolean;
};

export default function Toggle({
  checked,
  onChange,
  label,
  disabled = false,
}: ToggleProps) {
  return (
    <label className={`ui-toggle ${disabled ? "ui-toggle--disabled" : ""}`}>
      <span
        className={`ui-toggle__track ${checked ? "ui-toggle__track--on" : ""}`}
      >
        <input
          type="checkbox"
          checked={checked}
          disabled={disabled}
          onChange={(e) => onChange(e.target.checked)}
          className="ui-toggle__input"
        />
        <span className="ui-toggle__thumb" />
      </span>
      {label && <span className="ui-toggle__label">{label}</span>}
    </label>
  );
}
