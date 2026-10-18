"use client";
import { useRef, useState } from "react";
import { ApiError, structureKnowledge } from "@/lib/api";
import {
  captureFields,
  type CaptureResult,
  type CaptureReview,
  type CaptureSource,
  type CaptureStructure,
} from "@/lib/capture-structure";
import { ChecklistItem } from "./ui";
import type { AIExecution } from "@/lib/ai-models";
import { AIModelIndicator } from "./ai-model-indicator";
import { useAIConfiguration } from "./use-ai-configuration";

export function CaptureAI({
  source,
  disabled,
  onChange,
  onBusyChange,
  onProposalChange,
}: {
  source: CaptureSource;
  disabled: boolean;
  onChange: (value: CaptureReview | undefined) => void;
  onBusyChange: (busy: boolean) => void;
  onProposalChange: (exists: boolean) => void;
}) {
  const { configuration, loading: configurationLoading } = useAIConfiguration();
  const [busy, setBusy] = useState(false);
  const inFlight = useRef(false);
  const [error, setError] = useState("");
  const [result, setResult] = useState<CaptureResult | null>(null);
  const [fields, setFields] = useState<CaptureStructure | null>(null);
  const [execution, setExecution] = useState<AIExecution | null>(null);
  const [requestedSource, setRequestedSource] = useState("");
  const [reviewed, setReviewed] = useState(false);
  const signature = JSON.stringify(source);
  const stale = result !== null && signature !== requestedSource;
  const ready =
    source.title.length > 0 &&
    source.symptom.length > 0 &&
    source.content.length >= 10;

  async function structure() {
    if (inFlight.current || disabled || !ready) return;
    inFlight.current = true;
    setBusy(true);
    onBusyChange(true);
    setError("");
    setExecution(null);
    setReviewed(false);
    onChange(undefined);
    setRequestedSource(signature);
    try {
      const response = await structureKnowledge(source);
      setResult(response);
      onProposalChange(true);
      setFields(response.fields);
      setExecution(response.execution);
    } catch (e) {
      setError(
        `${(e as Error).message} You can submit the written observation manually.`,
      );
      if (e instanceof ApiError && e.execution) setExecution(e.execution);
    } finally {
      inFlight.current = false;
      setBusy(false);
      onBusyChange(false);
    }
  }

  function discard() {
    setResult(null);
    setExecution(null);
    onProposalChange(false);
    setFields(null);
    setReviewed(false);
    setError("");
    onChange(undefined);
  }

  return (
    <section aria-label="Optional AI structuring">
      <div className="section-heading">
        <h3>Optional AI organization</h3>
        <button
          type="button"
          className="button secondary"
          disabled={disabled || busy || !ready || result !== null}
          onClick={() => void structure()}
        >
          {busy ? "Structuring…" : "Structure with AI"}
        </button>
      </div>
      <AIModelIndicator
        configuration={configuration?.capture}
        execution={execution}
        loading={configurationLoading}
        label="Knowledge structuring model"
      />
      <p className="small-text muted">
        Sends these written fields to AMD Gemma. Attachments and audio are not
        processed. AI selects excerpts; its categorization is a proposal, not
        verified maintenance knowledge. Your original observation stays
        unchanged.
      </p>
      {busy && (
        <p role="status" className="small-text muted">
          Waiting for AMD Token Factory. No automatic retries or model fallback.
        </p>
      )}
      {error && (
        <p role="alert" className="form-error">
          {error}
        </p>
      )}
      {result && fields && (
        <>
          <p className="info-box">
            Review every category. Blank means not supplied. Keep uncertain
            causes uncertain; do not add unperformed repairs or verification.
          </p>
          {stale && (
            <p role="alert" className="form-error">
              Original fields changed after structuring. Discard this proposal
              to submit manually or structure the updated text.
            </p>
          )}
          {captureFields.map(([key, label]) => (
            <label key={key}>
              {label}
              <span className="field-hint">
                {result.proposal[key].length
                  ? `AI-selected excerpts from: ${[...new Set(result.proposal[key].map((q) => q.source))].join(", ")}. Your edits are technician supplied.`
                  : "Not supplied in the source. Add only facts you can confirm."}
              </span>
              <textarea
                rows={2}
                maxLength={1600}
                value={fields[key]}
                disabled={disabled || stale}
                onChange={(e) => {
                  setFields({ ...fields, [key]: e.target.value });
                  setReviewed(false);
                  onChange(undefined);
                }}
              />
            </label>
          ))}
          <ChecklistItem
            checked={reviewed}
            disabled={disabled || stale}
            onChange={() => {
              const next = !reviewed;
              setReviewed(next);
              onChange(
                next
                  ? { runId: result.runId, fields, reviewed: true }
                  : undefined,
              );
            }}
          >
            I reviewed and edited this proposed structure. It still requires
            supervisor approval.
          </ChecklistItem>
          <button
            type="button"
            className="button secondary"
            disabled={disabled || busy}
            onClick={discard}
          >
            Discard AI proposal; continue manually
          </button>
          {!reviewed && (
            <p className="small-text muted">
              To submit this structure, confirm review above. Otherwise discard
              it to submit only the original observation.
            </p>
          )}
        </>
      )}
    </section>
  );
}
