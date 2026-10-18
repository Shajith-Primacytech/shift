import type { AIExecution } from "./ai-models";

export const captureFields = [
  ["machineContext", "Machine and equipment context"],
  ["reportedSymptoms", "Reported symptoms"],
  ["faultCodes", "Fault codes, if supplied"],
  ["operatingConditions", "Operating conditions"],
  ["observations", "Technician observations"],
  ["confirmedRootCause", "Confirmed root cause, if known"],
  ["actionsPerformed", "Actions performed"],
  ["observedOutcome", "Observed outcome"],
  ["verificationSteps", "Verification steps"],
  ["safetyConsiderations", "Safety considerations"],
] as const;

export type CaptureField = (typeof captureFields)[number][0];
export type CaptureStructure = Record<CaptureField, string>;
export type CaptureSource = {
  machineId: string;
  title: string;
  symptom: string;
  content: string;
};
export type CaptureExecution = AIExecution & {
  provider: "AMD Token Factory";
  requested_model: string;
  requested_at: string;
  model_id: string;
  status: "success" | "failure";
};
export type CaptureResult = {
  runId: string;
  proposal: Record<CaptureField, { source: string; quote: string }[]>;
  fields: CaptureStructure;
  execution: CaptureExecution;
};
export type CaptureReview = {
  runId: string;
  fields: CaptureStructure;
  reviewed: true;
};
export type SavedCapture = {
  runId: string;
  original: CaptureSource;
  fields: CaptureStructure;
  execution: CaptureExecution;
};
