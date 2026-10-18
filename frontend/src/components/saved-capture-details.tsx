import { captureFields, type SavedCapture } from "@/lib/capture-structure";
import { CaptureExecution } from "./capture-execution";

export function SavedCaptureDetails({ capture }: { capture: SavedCapture }) {
  return (
    <section aria-label="Technician-reviewed AI structure">
      <h3 className="field-heading">
        AI-assisted structure · technician reviewed
      </h3>
      <p className="small-text muted">
        Gemma proposed the categories; the technician reviewed and may have
        edited them. Compare with the original observation above. This
        assistance does not grant approval or verify a repair.
      </p>
      <dl className="source-content">
        {captureFields.map(([key, label]) => (
          <div key={key}>
            <dt>
              <strong>{label}</strong>
            </dt>
            <dd>{capture.fields[key] || "Not supplied"}</dd>
          </div>
        ))}
      </dl>
      <CaptureExecution execution={capture.execution} />
    </section>
  );
}
