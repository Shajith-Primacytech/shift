"use client";
import { useState } from "react";
import { useSearchParams } from "next/navigation";
import Link from "next/link";
import {
  Search,
  Plus,
  BookOpen,
  ShieldCheck,
  ArrowUpRight,
  X,
} from "lucide-react";
import { useKnowledge } from "./knowledge-provider";
import { DemoNotice, PageHeading, EmptyState, StatusBadge } from "./ui";
import { machines } from "@/lib/demo-data";
import { AttachmentPreview } from "./attachment-preview";
export function KnowledgeLibrary() {
  const params = useSearchParams();
  const { records } = useKnowledge();
  const [query, setQuery] = useState(params.get("q") || "");
  const [machine, setMachine] = useState("All machines");
  const [kind, setKind] = useState("All types");
  const [selectedId, setSelectedId] = useState<string | null>(params.get("id"));
  const approved = records.filter((r) => r.status === "Approved");
  const filtered = approved.filter(
    (r) =>
      `${r.title} ${r.content} ${r.machineId} ${r.symptom}`
        .toLowerCase()
        .includes(query.toLowerCase()) &&
      (machine === "All machines" || r.machineId === machine) &&
      (kind === "All types" || r.kind === kind),
  );
  const selected = approved.find((r) => r.id === selectedId);
  return (
    <>
      <PageHeading
        eyebrow="THE TEAM’S SHARED EXPERIENCE"
        title="Good knowledge keeps working."
        description="Find approved procedures, field observations, and lessons from the floor."
        action={
          <Link href="/knowledge/capture" className="button primary">
            <Plus size={17} />
            Capture knowledge
          </Link>
        }
      />
      <DemoNotice>
        Local knowledge library · Human-authored synthetic examples and saved
        submissions. Supervisor decisions are saved; only currently approved knowledge
        is eligible for troubleshooting retrieval.
      </DemoNotice>
      <div className="filter-bar">
        <div className="input-with-icon">
          <Search size={18} />
          <input
            aria-label="Search approved knowledge"
            placeholder="Search symptoms, procedures, or machine IDs…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <select
          aria-label="Filter knowledge by machine"
          value={machine}
          onChange={(e) => setMachine(e.target.value)}
        >
          <option>All machines</option>
          {machines.map((m) => (
            <option key={m.id}>{m.id}</option>
          ))}
        </select>
        <select
          aria-label="Filter knowledge by type"
          value={kind}
          onChange={(e) => setKind(e.target.value)}
        >
          {["All types", "SOP", "Field note", "Resolution"].map((t) => (
            <option key={t}>{t}</option>
          ))}
        </select>
      </div>
      <div className="results-label">
        <span role="status">{filtered.length} approved resources</span>
        <span>
          <ShieldCheck size={14} /> Pending and rejected notes are excluded
        </span>
      </div>
      {selectedId && !selected && (
        <div className="info-box">
          <BookOpen size={18} />
          <p>This source is unavailable or has not been approved.</p>
          <button className="text-link" onClick={() => setSelectedId(null)}>
            Dismiss
          </button>
        </div>
      )}
      <div
        className={selected ? "library-layout has-selection" : "library-layout"}
      >
        <div className="knowledge-grid">
          {filtered.map((record) => (
            <button
              key={record.id}
              className={`knowledge-card ${selected?.id === record.id ? "selected" : ""}`}
              onClick={() => setSelectedId(record.id)}
              aria-pressed={selected?.id === record.id}
            >
              <div className="section-heading">
                <span className="document-icon">
                  <BookOpen size={22} />
                </span>
                <span className="resource-kind">{record.kind}</span>
              </div>
              <h2>{record.title}</h2>
              <p>{record.symptom}</p>
              <div className="knowledge-tags">
                <span>{record.machineId}</span>
                <span>{record.id}</span>
              </div>
              <div className="knowledge-card-footer">
                <span>
                  <ShieldCheck size={14} />
                  Approved demo
                </span>
                <ArrowUpRight size={17} />
              </div>
            </button>
          ))}
          {!filtered.length && (
            <EmptyState icon={Search} title="No matching knowledge">
              Try a broader term or clear your filters. Only approved records
              appear here.
            </EmptyState>
          )}
        </div>
        {selected && (
          <article
            className="panel source-reader"
            aria-label="Selected knowledge source"
          >
            <div className="section-heading">
              <span className="eyebrow">SOURCE / {selected.id}</span>
              <button
                className="icon-button"
                onClick={() => setSelectedId(null)}
                aria-label="Close source"
              >
                <X size={19} />
              </button>
            </div>
            <h2>{selected.title}</h2>
            <div className="reader-meta">
              <StatusBadge status={selected.status} />
              <span>
                {selected.machineId} · {selected.kind}
              </span>
            </div>
            <div className="source-content">{selected.content}</div>
            {selected.attachments?.map((a, i) => (
              <AttachmentPreview key={i} attachment={a} />
            ))}
            <div className="review-attribution">
              <ShieldCheck size={17} />
              <div>
                Reviewed by <strong>{selected.reviewer}</strong>
                <span>
                  Demo approval ·{" "}
                  {selected.reviewedAt?.slice(0, 10) || selected.date}
                </span>
              </div>
            </div>
          </article>
        )}
      </div>
    </>
  );
}
