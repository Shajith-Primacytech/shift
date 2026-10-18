export type AIExecution = {
  provider: string;
  requested_model: string | null;
  returned_model?: string | null;
  requested_at: string | null;
  latency_ms: number | null;
  usage: {
    prompt_tokens?: number | null;
    completion_tokens?: number | null;
    total_tokens?: number | null;
    reasoning_tokens?: number | null;
  } | null;
  status: "success" | "failure" | "interrupted";
  http_status: number | null;
  error_code: string | null;
};
export type AIModelConfiguration = {
  provider: string;
  requested_model: string | null;
  developer?: string;
  status: "configured" | "unavailable";
};
export type AIConfiguration = {
  capture: AIModelConfiguration;
  troubleshooting: AIModelConfiguration;
};
