"use client";
import Link from "next/link";
import { useState } from "react";
import {
  ArrowLeft,
  Sparkles,
  Plus,
  Thermometer,
  Gauge,
  Activity,
  BookOpen,
  ArrowUpRight,
  ShieldCheck,
} from "lucide-react";
import { type Machine } from "@/lib/demo-data";
import { useKnowledge } from "./knowledge-provider";
import {
  DemoNotice,
  PageHeading,
  StatusBadge,
  SectionHeading,
  EmptyState,
} from "./ui";
import { MachineIllustration } from "./machine-illustration";
export function MachineDetail({ machine: m }: { machine: Machine }) {
  const [tab, setTab] = useState("Overview");
  const { records } = useKnowledge();
  const relevant = records.filter((r) => r.machineId === m.id);
  return (
    <>
      <Link href="/machines" className="back-link">
        <ArrowLeft size={15} />
        All machines
      </Link>
      <PageHeading
        eyebrow={`${m.area.toUpperCase()} / ${m.category.toUpperCase()}`}
        title={m.id}
        description={m.name}
        action={
          <div className="button-group">
            <Link
              className="button secondary"
              href={`/knowledge/capture?machine=${m.id}`}
            >
              <Plus size={16} />
              Log observation
            </Link>
            <Link
              className="button primary"
              href={`/troubleshoot?machine=${m.id}`}
            >
              <Sparkles size={16} />
              Troubleshoot
            </Link>
          </div>
        }
      />
      <DemoNotice />
      <div className="tabs" role="tablist" aria-label="Machine information">
        {["Overview", "Knowledge", "History"].map((t) => (
          <button
            key={t}
            id={`tab-${t}`}
            aria-controls="machine-tab-panel"
            role="tab"
            aria-selected={tab === t}
            onClick={() => setTab(t)}
            className={tab === t ? "active" : ""}
          >
            {t}
            {t === "Knowledge" && (
              <span>
                {relevant.filter((r) => r.status === "Approved").length}
              </span>
            )}
          </button>
        ))}
      </div>
      <div
        id="machine-tab-panel"
        role="tabpanel"
        aria-labelledby={`tab-${tab}`}
      >
        {tab === "Overview" && (
          <>
            <div className="detail-grid">
              <section className="panel detail-visual">
                <div className="section-heading">
                  <span className="eyebrow">ASSET OVERVIEW</span>
                  <StatusBadge status={m.status} />
                </div>
                <MachineIllustration />
                <div className="asset-label">
                  <span>
                    Asset ID <strong>{m.id}</strong>
                  </span>
                  <span>
                    Location <strong>{m.area}</strong>
                  </span>
                  <span>
                    Type <strong>{m.category}</strong>
                  </span>
                </div>
              </section>
              <section className="panel">
                <SectionHeading
                  title="Operating snapshot"
                  subtitle="Simulated readings · not connected to equipment"
                />
                {[
                  {
                    icon: Thermometer,
                    label: "Temperature",
                    value: `${m.temperature} °C`,
                  },
                  {
                    icon: Gauge,
                    label: "Spindle / motor speed",
                    value: `${m.rpm.toLocaleString("en-US")} RPM`,
                  },
                  {
                    icon: Activity,
                    label: "Vibration",
                    value: `${m.vibration} mm/s`,
                  },
                ].map(({ icon: Icon, label, value }) => (
                  <div className="reading-row" key={label}>
                    <div className="metric-icon">
                      <Icon size={21} />
                    </div>
                    <div>
                      <p>{label}</p>
                      <strong>{value}</strong>
                    </div>
                    <span className="small-text muted">Demo</span>
                  </div>
                ))}
                <div className="info-box">
                  <ShieldCheck size={18} />
                  <p>
                    Readings are synthetic. Use approved site procedures and
                    qualified judgment for real equipment.
                  </p>
                </div>
              </section>
            </div>
            <section className="panel detail-summary">
              <SectionHeading title="Latest shift note" />
              <p>{m.note}. This is a synthetic demonstration snapshot.</p>
              <Link
                href={`/knowledge/capture?machine=${m.id}`}
                className="text-link"
              >
                Add your observation
                <ArrowRightIcon />
              </Link>
            </section>
          </>
        )}
        {tab === "Knowledge" && (
          <section className="panel">
            <SectionHeading title="Approved machine knowledge" />
            {relevant
              .filter((r) => r.status === "Approved")
              .map((r) => (
                <Link
                  key={r.id}
                  href={`/knowledge?id=${r.id}`}
                  className="knowledge-row"
                >
                  <BookOpen size={22} />
                  <div>
                    <h3>{r.title}</h3>
                    <p>
                      {r.id} · {r.kind}
                    </p>
                  </div>
                  <StatusBadge status={r.status} />
                  <ArrowUpRight size={17} />
                </Link>
              ))}
            {!relevant.some((r) => r.status === "Approved") && (
              <EmptyState title="No approved knowledge yet">
                Capture an observation and send it through the demo review
                queue.
              </EmptyState>
            )}
          </section>
        )}
        {tab === "History" && (
          <section className="panel">
            <SectionHeading
              title="Knowledge activity"
              subtitle="Synthetic records and saved submissions"
            />
            {relevant.length ? (
              relevant.map((r) => (
                <div key={r.id} className="knowledge-row">
                  <BookOpen size={20} />
                  <div>
                    <h3>{r.title}</h3>
                    <p>
                      {r.date} · {r.author}
                    </p>
                  </div>
                  <StatusBadge status={r.status} />
                </div>
              ))
            ) : (
              <EmptyState title="No activity yet">
                Observations for this machine will appear here during this
                workspace.
              </EmptyState>
            )}
          </section>
        )}
      </div>
    </>
  );
}
function ArrowRightIcon() {
  return <ArrowUpRight size={15} />;
}
