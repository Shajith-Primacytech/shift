"use client";
import { useState } from "react";
import {
  Check,
  CheckCircle2,
  ClipboardCheck,
  ShieldCheck,
  X,
} from "lucide-react";
import { useKnowledge } from "@/components/knowledge-provider";
import {
  DemoNotice,
  EmptyState,
  PageHeading,
  StatusBadge,
} from "@/components/ui";
import { AttachmentPreview } from "@/components/attachment-preview";
export default function ApprovalsPage() {
  const { records, review, user, refresh } = useKnowledge();
  const [busy, setBusy] = useState(false);
  const [filter, setFilter] = useState("Pending");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const reviewer = user.name;
  const [note, setNote] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const visible = records.filter((r) => r.status === filter);
  const selected = visible.find((r) => r.id === selectedId) || visible[0];
  async function decide(status: "Approved" | "Rejected" | "Revoked") {
    if (!selected) return;
    if (!reviewer.trim()) {
      setError("Enter a reviewer name.");
      return;
    }
    if (status !== "Approved" && !note.trim()) {
      setError("Add a reason so the technician knows what to improve.");
      return;
    }
    setBusy(true);
    try {
      await review(selected.id, status, note.trim());
      setMessage(`${selected.id} ${status.toLowerCase()} and saved.`);
      setNote("");
      setError("");
      setSelectedId(null);
    } catch (error) {
      setError((error as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      <PageHeading
        eyebrow="HUMAN JUDGMENT, AT THE CENTER"
        title="Turn observations into knowledge."
        description="Review the context. Preserve the facts. Help the next technician."
      />
      <DemoNotice>
        {user.role === "supervisor"
          ? "Supervisor workspace · Reviews are saved with your authenticated identity. Synthetic factory data only."
          : "Your submissions · A supervisor must review your observations. Only approved records enter the knowledge library."}
      </DemoNotice>
      <button
        className="button secondary"
        disabled={busy}
        onClick={async () => {
          setBusy(true);
          try {
            await refresh();
            setError("");
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        Refresh queue
      </button>
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
      <div className="review-summary">
        <div>
          <ClipboardCheck size={21} />
          <strong>
            {records.filter((r) => r.status === "Pending").length}
          </strong>
          <span>awaiting review</span>
        </div>
        <div>
          <ShieldCheck size={21} />
          <strong>
            {records.filter((r) => r.status === "Approved").length}
          </strong>
          <span>approved resources</span>
        </div>
      </div>
      <div className="tabs" aria-label="Filter review status">
        {["Pending", "Approved", "Rejected", "Revoked"].map((s) => (
          <button
            key={s}
            className={filter === s ? "active" : ""}
            aria-pressed={filter === s}
            onClick={() => {
              setFilter(s);
              setSelectedId(null);
              setNote("");
              setError("");
            }}
          >
            {s}
            <span>{records.filter((r) => r.status === s).length}</span>
          </button>
        ))}
      </div>
      {message && (
        <div className="success-banner" role="status">
          <CheckCircle2 size={17} />
          {message}
          <button
            className="icon-button"
            onClick={() => setMessage("")}
            aria-label="Dismiss review confirmation"
          >
            <X size={16} />
          </button>
        </div>
      )}
      {selected ? (
        <div className="review-layout">
          <div className="review-list">
            {visible.map((r) => (
              <button
                key={r.id}
                className={`review-list-item ${selected.id === r.id ? "active" : ""}`}
                onClick={() => {
                  setSelectedId(r.id);
                  setNote("");
                  setError("");
                }}
                aria-pressed={selected.id === r.id}
              >
                <div>
                  <span className="mono">{r.machineId}</span>
                  <StatusBadge status={r.status} />
                </div>
                <h3>{r.title}</h3>
                <p>
                  {r.author} · {r.date}
                </p>
              </button>
            ))}
          </div>
          <article className="panel review-detail">
            <div className="section-heading">
              <span className="eyebrow">SUBMISSION / {selected.id}</span>
              <StatusBadge status={selected.status} />
            </div>
            <h2>{selected.title}</h2>
            <p className="muted">
              {selected.machineId} · {selected.symptom}
            </p>
            <div className="review-author">
              <div className="avatar">
                {selected.author
                  .split(" ")
                  .map((n) => n[0])
                  .slice(0, 2)
                  .join("")}
              </div>
              <div>
                <strong>{selected.author}</strong>
                <span>
                  Submitted {selected.date} · {selected.kind}
                </span>
              </div>
            </div>
            <h3 className="field-heading">Original observation</h3>
            <div className="source-content observation-content">
              {selected.content}
            </div>
            {selected.attachments?.map((a, i) => (
              <AttachmentPreview key={i} attachment={a} />
            ))}
            {user.role === "supervisor" &&
            (selected.status === "Pending" ||
              selected.status === "Approved") ? (
              <>
                <div className="info-box">
                  <ShieldCheck size={18} />
                  <p>
                    Review the written facts and any attachments. Approval makes
                    this entry visible in the demo library; it does not validate
                    it for real maintenance.
                  </p>
                </div>
                <label>
                  Reviewer name
                  <input maxLength={80} value={reviewer} readOnly />
                </label>
                <label>
                  Review note{" "}
                  <span className="field-hint">
                    Required when rejecting or revoking
                  </span>
                  <textarea
                    rows={3}
                    maxLength={2000}
                    value={note}
                    onChange={(e) => setNote(e.target.value)}
                    placeholder="What should the next technician know?"
                  />
                </label>
                {error && (
                  <p className="form-error" role="alert">
                    {error}
                  </p>
                )}
                <div className="review-actions">
                  <button
                    className="button danger-outline"
                    disabled={busy}
                    onClick={() =>
                      decide(
                        selected.status === "Approved" ? "Revoked" : "Rejected",
                      )
                    }
                  >
                    <X size={17} />
                    {selected.status === "Approved"
                      ? "Revoke approval"
                      : "Reject submission"}
                  </button>
                  {selected.status === "Pending" && (
                    <button
                      disabled={busy}
                      className="button primary"
                      onClick={() => decide("Approved")}
                    >
                      <Check size={17} />
                      Approve for library
                    </button>
                  )}
                </div>
              </>
            ) : (
              <div className="review-attribution">
                <ShieldCheck size={20} />
                <div>
                  <strong>
                    {selected.status}
                    {selected.reviewer
                      ? ` by ${selected.reviewer}`
                      : " — awaiting supervisor review"}
                  </strong>
                  <span>
                    {selected.reviewNote || "No additional review note."}
                  </span>
                </div>
              </div>
            )}
          </article>
        </div>
      ) : (
        <EmptyState
          icon={ClipboardCheck}
          title={
            filter === "Pending"
              ? "The queue is clear."
              : `No ${filter.toLowerCase()} submissions`
          }
        >
          {filter === "Pending"
            ? "New captured observations and troubleshooting outcomes will appear here."
            : "Saved review decisions will appear here."}
        </EmptyState>
      )}
    </>
  );
}
