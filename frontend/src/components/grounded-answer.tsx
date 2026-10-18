"use client";
import Link from "next/link";
import { BookOpen, ShieldCheck, Sparkles } from "lucide-react";
import type { TroubleshootingAnswer } from "@/lib/api";
import type { AIExecution } from "@/lib/ai-models";
import { AIModelIndicator } from "./ai-model-indicator";
import { EmptyState } from "./ui";

export function GroundedAnswer({
  answer,
  loading,
  error,
  retry,
  failureExecution,
}: {
  answer: TroubleshootingAnswer | null;
  loading: boolean;
  error: string;
  retry: () => void;
  failureExecution?: AIExecution | null;
}) {
  if (loading)
    return (
      <div className="info-box" role="status">
        <Sparkles size={20} />
        <p>
          Retrieving approved evidence and asking AMD… This can take up to a
          minute.
        </p>
      </div>
    );
  if (error)
    return (
      <div className="guidance-box">
        <p role="alert" className="form-error">
          {error}
        </p>
        <p>No maintenance answer was displayed.</p>
        {failureExecution && (
          <AIModelIndicator
            execution={failureExecution}
            label="Troubleshooting evidence selection"
          />
        )}
        <button className="button secondary" onClick={retry}>
          Retry troubleshooting
        </button>
      </div>
    );
  if (!answer) return null;
  if (answer.status === "insufficient_evidence")
    return (
      <>
        <EmptyState icon={BookOpen} title="Insufficient approved evidence">
          {answer.message}
        </EmptyState>
        {answer.execution ? (
          <AIModelIndicator
            execution={answer.execution}
            label="Troubleshooting evidence selection"
          />
        ) : (
          <p className="small-text muted">
            No model execution for this response.
          </p>
        )}
      </>
    );
  return (
    <>
      <div className="guidance-box">
        <div>
          <Sparkles size={21} />
          <strong>AI-selected approved guidance</strong>
          <span className="resource-kind">VERIFIED QUOTES</span>
        </div>
        <p>{answer.message}</p>
        {answer.execution ? (
          <AIModelIndicator
            execution={answer.execution}
            label="Troubleshooting evidence selection"
          />
        ) : (
          <p className="small-text muted">
            Execution metadata unavailable; model attribution is not confirmed.
          </p>
        )}
        {answer.steps.map((step, i) => (
          <div className="hypothesis" key={`${step.citation_id}-${i}`}>
            <span>{String(i + 1).padStart(2, "0")}</span>
            <div>
              <p>{step.text}</p>
              <a
                className="back-link"
                href={`#source-${answer.citations.findIndex((c) => c.id === step.citation_id)}`}
              >
                Source{" "}
                {answer.citations.findIndex((c) => c.id === step.citation_id) +
                  1}
              </a>
            </div>
          </div>
        ))}
      </div>
      <div className="evidence-note">
        <ShieldCheck size={18} />
        <div>
          <strong>Evidence coverage is limited</strong>
          <p>{answer.uncertainty}</p>
          <p className="small-text">
            Hybrid retrieval ·{" "}
            {answer.latency_ms == null
              ? ""
              : `${(answer.latency_ms / 1000).toFixed(1)}s inference`}{" "}
            · No calibrated confidence score
          </p>
        </div>
      </div>
      <h3 className="field-heading">Supporting sources</h3>
      <div className="source-cards">
        {answer.citations.map((source, i) => (
          <article
            className="source-card rag-source"
            id={`source-${i}`}
            key={source.id}
          >
            <span className="document-icon">
              <BookOpen size={19} />
            </span>
            <div>
              <h3>
                Source {i + 1}: {source.title}
              </h3>
              <p>
                {source.record_id} · {source.version_id} · {source.machine_id}
              </p>
              <details>
                <summary>Inspect retrieved passage</summary>
                <p className="source-content">{source.excerpt}</p>
                <small>Chunk: {source.id}</small>
              </details>
              <Link
                className="back-link"
                href={`/knowledge?id=${encodeURIComponent(source.record_id)}`}
              >
                Open approved record
              </Link>
            </div>
          </article>
        ))}
      </div>
    </>
  );
}
