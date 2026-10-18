import type { AIExecution, AIModelConfiguration } from "@/lib/ai-models";

export function AIModelIndicator({
  configuration,
  execution,
  loading = false,
  label = "AI model",
}: {
  configuration?: AIModelConfiguration;
  execution?: AIExecution | null;
  loading?: boolean;
  label?: string;
}) {
  const returned = execution?.returned_model;
  const gemma = execution
    ? returned === "Gemma-4-31B-IT" || returned === "self-dploy/Gemma-4-31B-IT"
    : configuration?.developer === "Google" &&
      configuration.requested_model === "Gemma-4-31B-IT";
  const provider = execution?.provider || configuration?.provider;
  return (
    <section aria-label={label} className="small-text">
      <p>
        <strong>{gemma ? "Powered by Google Gemma" : label}</strong>
      </p>
      <p className="mono">
        {execution
          ? returned || "Returned model not recorded"
          : configuration?.requested_model ||
            (loading
              ? "Loading model configuration…"
              : "Model configuration unavailable")}
      </p>
      {provider && <p className="muted">Inference via {provider}</p>}
      <p className="muted" role="status">
        {execution
          ? `Execution ${execution.status}`
          : configuration?.status === "configured"
            ? "Configured · not executed for this draft"
            : loading
              ? "Checking configuration · no inference requested"
              : "Unavailable · no inference requested"}
      </p>
      {execution && (
        <details className="muted">
          <summary>
            AI Execution Details · {execution.provider} · {execution.status}
          </summary>
          <dl>
            <dt>Provider</dt>
            <dd>{execution.provider}</dd>
            <dt>Requested model</dt>
            <dd>{execution.requested_model || "Not recorded"}</dd>
            <dt>Returned model</dt>
            <dd>{returned || "Not recorded by this execution"}</dd>
            <dt>Execution status</dt>
            <dd>{execution.status}</dd>
            <dt>Timestamp (UTC)</dt>
            <dd>{execution.requested_at || "Not recorded"}</dd>
            <dt>Latency</dt>
            <dd>
              {execution.latency_ms == null
                ? "Not provided"
                : `${(execution.latency_ms / 1000).toFixed(2)} s`}
            </dd>
            <dt>Tokens (prompt / completion / total)</dt>
            <dd>
              {execution.usage?.prompt_tokens ?? "—"} /{" "}
              {execution.usage?.completion_tokens ?? "—"} /{" "}
              {execution.usage?.total_tokens ?? "—"}
            </dd>
            <dt>Provider HTTP status</dt>
            <dd>{execution.http_status ?? "Not provided"}</dd>
            {execution.error_code && (
              <>
                <dt>Failure category</dt>
                <dd>{execution.error_code}</dd>
              </>
            )}
          </dl>
        </details>
      )}
    </section>
  );
}
