import type { ButtonHTMLAttributes, ReactNode } from "react";
import "./Button.css";

type ButtonVariant = "primary" | "secondary" | "ghost" | "danger";

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: ButtonVariant;
  icon?: ReactNode;
  fullWidth?: boolean;
};

export default function Button({
  variant = "primary",
  icon,
  fullWidth = false,
  className,
  children,
  ...rest
}: ButtonProps) {
  const classes = [
    "ui-button",
    `ui-button--${variant}`,
    fullWidth ? "ui-button--full" : "",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <button className={classes} {...rest}>
      {icon && <span className="ui-button__icon">{icon}</span>}
      {children}
    </button>
  );
}
