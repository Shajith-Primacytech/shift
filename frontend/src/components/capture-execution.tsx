import type { CaptureExecution as Execution } from "@/lib/capture-structure";
import { AIModelIndicator } from "./ai-model-indicator";

export function CaptureExecution({ execution }: { execution: Execution }) {
  return (
    <AIModelIndicator
      execution={execution}
      label="Knowledge structuring model"
    />
  );
}
