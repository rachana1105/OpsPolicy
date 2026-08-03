import type { ReactNode } from "react";

const RISK_STYLES: Record<string, string> = {
  LOW: "bg-success-soft text-success",
  MEDIUM: "bg-warning-soft text-warning",
  HIGH: "bg-danger-soft text-danger",
  CRITICAL: "bg-danger text-white",
};

const DECISION_STYLES: Record<string, string> = {
  AUTO_APPROVE: "bg-success-soft text-success",
  REQUIRES_APPROVAL: "bg-info-soft text-info",
  REJECT: "bg-danger-soft text-danger",
  REQUIRES_EXCEPTION: "bg-warning-soft text-warning",
};

const STATUS_STYLES: Record<string, string> = {
  DRAFT: "bg-line text-muted",
  SUBMITTED: "bg-info-soft text-info",
  APPROVED: "bg-success-soft text-success",
  ACTIVE: "bg-secondary-soft text-secondary",
  REJECTED: "bg-danger-soft text-danger",
  REVOKED: "bg-line text-muted",
  PUBLISHED: "bg-success-soft text-success",
};

export function RiskBadge({ level }: { level: string }) {
  return (
    <span className={`chip ${RISK_STYLES[level] ?? "bg-line text-muted"}`}>
      {level}
    </span>
  );
}

export function DecisionBadge({ decision }: { decision: string }) {
  return (
    <span className={`chip ${DECISION_STYLES[decision] ?? "bg-line text-muted"}`}>
      {decision.replace(/_/g, " ")}
    </span>
  );
}

export function StatusBadge({ status }: { status: string }) {
  return (
    <span className={`chip ${STATUS_STYLES[status] ?? "bg-line text-muted"}`}>
      {status.replace(/_/g, " ")}
    </span>
  );
}

export function Chip({
  children,
  tone = "muted",
}: {
  children: ReactNode;
  tone?: "muted" | "primary" | "secondary" | "warning";
}) {
  const tones = {
    muted: "bg-line text-muted",
    primary: "bg-primary-soft text-primary-deep",
    secondary: "bg-secondary-soft text-secondary",
    warning: "bg-warning-soft text-warning",
  };
  return <span className={`chip ${tones[tone]}`}>{children}</span>;
}
