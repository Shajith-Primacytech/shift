import Link from "next/link";
import {
  ArrowUpRight,
  ArrowRight,
  Check,
  Circle,
  Database,
  type LucideIcon,
} from "lucide-react";
import type { ReactNode } from "react";
export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "green" | "amber" | "blue" | "neutral" | "red";
}) {
  return (
    <span className={`badge ${tone}`}>
      <Circle size={6} fill="currentColor" />
      {children}
    </span>
  );
}
export function StatusBadge({ status }: { status: string }) {
  return (
    <Badge
      tone={
        status === "Running" || status === "Approved"
          ? "green"
          : status === "Attention" || status === "Pending"
            ? "amber"
            : status === "Rejected"
              ? "red"
              : "neutral"
      }
    >
      {status}
    </Badge>
  );
}
export function PageHeading({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <div className="eyebrow">{eyebrow}</div>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function DemoNotice({ children }: { children?: ReactNode }) {
  return (
    <div className="demo-notice">
      <Database size={15} />
      <span>
        {children || (
          <>
            Demo workspace · All machines, telemetry, and knowledge are
            synthetic. Knowledge submissions and reviews are saved locally.
          </>
        )}
      </span>
    </div>
  );
}
export function SectionHeading({
  title,
  subtitle,
  href,
  linkText = "View all",
}: {
  title: string;
  subtitle?: string;
  href?: string;
  linkText?: string;
}) {
  return (
    <div className="section-heading">
      <div>
        <h2>{title}</h2>
        {subtitle && <p>{subtitle}</p>}
      </div>
      {href && (
        <Link href={href} className="text-link">
          {linkText}
          <ArrowRight size={15} />
        </Link>
      )}
    </div>
  );
}
export function EmptyState({
  icon: Icon = Database,
  title,
  children,
}: {
  icon?: LucideIcon;
  title: string;
  children: ReactNode;
}) {
  return (
    <div className="empty-state">
      <Icon size={30} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
export function ActionLink({
  href,
  icon: Icon,
  title,
  description,
}: {
  href: string;
  icon: LucideIcon;
  title: string;
  description: string;
}) {
  return (
    <Link href={href} className="action-card">
      <div className="action-icon">
        <Icon size={21} />
      </div>
      <div>
        <h3>{title}</h3>
        <p>{description}</p>
      </div>
      <ArrowUpRight size={17} className="muted" />
    </Link>
  );
}
export function ChecklistItem({
  checked,
  onChange,
  children,
}: {
  checked: boolean;
  onChange: () => void;
  children: ReactNode;
}) {
  return (
    <label className={`check-row ${checked ? "checked" : ""}`}>
      <input type="checkbox" checked={checked} onChange={onChange} />
      <span className="check-visual">{checked && <Check size={14} />}</span>
      <span>{children}</span>
    </label>
  );
}
