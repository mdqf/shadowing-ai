import type { ReactNode } from "react";
import "./EmptyState.css";

type EmptyStateProps = {
  icon?: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
};

export default function EmptyState({
  icon,
  title,
  description,
  action,
}: EmptyStateProps) {
  return (
    <div className="ui-empty-state">
      {icon && <div className="ui-empty-state__icon">{icon}</div>}
      <div className="ui-empty-state__title">{title}</div>
      {description && (
        <div className="ui-empty-state__description">{description}</div>
      )}
      {action && <div className="ui-empty-state__action">{action}</div>}
    </div>
  );
}
