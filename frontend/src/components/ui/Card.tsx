import type { HTMLAttributes } from "react";
import "./Card.css";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  /** Matches the existing surface depth hierarchy: 1 = biggest
   * outer container, 3 = smallest nested card. */
  level?: 1 | 2 | 3;
};

export default function Card({
  level = 1,
  className,
  children,
  ...rest
}: CardProps) {
  const classes = ["ui-card", `ui-card--level-${level}`, className ?? ""]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={classes} {...rest}>
      {children}
    </div>
  );
}
