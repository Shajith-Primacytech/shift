import type { KnowledgeRecord } from "./demo-data";

export type User = {
  id: string;
  username: string;
  name: string;
  role: "technician" | "supervisor";
};
export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
  }
}
// Match the browser hostname so localhost and 127.0.0.1 both use same-site cookies.
export function apiBase() {
  return (
    process.env.NEXT_PUBLIC_API_URL ||
    `http://${typeof window === "undefined" ? "localhost" : window.location.hostname}:8000`
  );
}
export async function api<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${apiBase()}/api/v1${path}`, {
      ...options,
      credentials: "include",
      cache: "no-store",
      signal: options.signal || AbortSignal.timeout(30000),
      headers: { "X-Shift-Request": "1", ...options.headers },
    });
  } catch {
    throw new ApiError(
      "Cannot reach SHIFT. Check the backend connection and retry.",
      0,
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new ApiError(
      typeof body.detail === "string"
        ? body.detail
        : "The request could not be completed. Check your input.",
      response.status,
    );
  }
  return response.status === 204 ? (undefined as T) : response.json();
}
export function jsonRequest(body: unknown): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}
export type NewKnowledge = Pick<
  KnowledgeRecord,
  "title" | "machineId" | "symptom" | "content" | "kind" | "attachments"
>;
export const knowledgeApi = {
  approved: () => api<KnowledgeRecord[]>("/knowledge"),
  submissions: () => api<KnowledgeRecord[]>("/submissions"),
  submit: (record: NewKnowledge) => {
    const { attachments, ...metadata } = record;
    const data = new FormData();
    data.append("metadata", JSON.stringify(metadata));
    for (const attachment of attachments || []) {
      if (attachment.file)
        data.append("files", attachment.file, attachment.name);
    }
    return api<KnowledgeRecord>("/submissions", { method: "POST", body: data });
  },
  review: (
    record: KnowledgeRecord,
    decision: "Approved" | "Rejected" | "Revoked",
    note: string,
  ) =>
    api<KnowledgeRecord>(
      `/submissions/${record.id}/review`,
      jsonRequest({ versionId: record.versionId, decision, note }),
    ),
};

export type TroubleshootingAnswer = {
  status: "answered" | "insufficient_evidence";
  mode: "ai_selected_quotes" | "no_generation";
  message: string;
  steps: { text: string; citation_id: string }[];
  citations: {
    id: string;
    record_id: string;
    version_id: string;
    machine_id: string;
    title: string;
    excerpt: string;
  }[];
  uncertainty: string;
  retrieval_mode: "hybrid";
  model: string | null;
  latency_ms: number | null;
  usage: { total_tokens?: number | null } | null;
};
export function askTroubleshooting(machine_id: string, question: string) {
  return api<TroubleshootingAnswer>("/troubleshoot", {
    ...jsonRequest({ machine_id, question }),
    signal: AbortSignal.timeout(75000),
  });
}
