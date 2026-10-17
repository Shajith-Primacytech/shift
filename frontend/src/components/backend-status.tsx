"use client";
import { useCallback, useEffect, useState } from "react";
import { apiBase } from "@/lib/api";
import { RefreshCw } from "lucide-react";
export function BackendStatus() {
  const [status, setStatus] = useState<"loading" | "online" | "offline">(
    "loading",
  );
  const check = useCallback((signal?: AbortSignal) => {
    const combined = signal
      ? AbortSignal.any([signal, AbortSignal.timeout(5000)])
      : AbortSignal.timeout(5000);
    return fetch(`${apiBase()}/api/v1/health`, { signal: combined })
      .then(async (response) => {
        if (!response.ok) throw new Error("Unavailable");
        const data = await response.json();
        if (data.status !== "ok" || data.service !== "shift-api")
          throw new Error("Invalid health response");
        if (!signal?.aborted) setStatus("online");
      })
      .catch(() => {
        if (!signal?.aborted) setStatus("offline");
      });
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    void check(controller.signal);
    return () => controller.abort();
  }, [check]);
  return (
    <div className="backend-status">
      <span className={`status-dot ${status}`} />
      <span role="status">
        {status === "loading"
          ? "Checking API…"
          : status === "online"
            ? "SHIFT API connected"
            : "API offline · saved data unavailable"}
      </span>
      <button
        className="icon-button small"
        aria-label="Recheck backend connection"
        disabled={status === "loading"}
        onClick={() => {
          setStatus("loading");
          void check();
        }}
      >
        <RefreshCw size={13} />
      </button>
    </div>
  );
}
