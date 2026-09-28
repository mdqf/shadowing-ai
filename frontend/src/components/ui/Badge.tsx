import type { ReactNode } from "react";
import "./Badge.css";

type BadgeVariant = "success" | "warning" | "danger" | "info" | "neutral";

type BadgeProps = {
  variant?: BadgeVariant;
  children: ReactNode;
};

export default function Badge({ variant = "neutral", children }: BadgeProps) {
  return <span className={`ui-badge ui-badge--${variant}`}>{children}</span>;
}
