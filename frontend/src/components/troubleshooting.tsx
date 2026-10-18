"use client";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { useState } from "react";
import {
  Activity,
  ArrowLeft,
  ArrowRight,
  Check,
  CheckCircle2,
  ChevronRight,
  CircleAlert,
  ClipboardCheck,
  FileText,
  HelpCircle,
  ShieldCheck,
  Sparkles,
  Thermometer,
  Volume2,
  Wrench,
} from "lucide-react";
import {
  ApiError,
  askTroubleshooting,
  type TroubleshootingAnswer,
} from "@/lib/api";
import type { AIExecution } from "@/lib/ai-models";
import { GroundedAnswer } from "./grounded-answer";
import { machines } from "@/lib/demo-data";
import { useKnowledge } from "./knowledge-provider";
import { Badge, ChecklistItem, DemoNotice, PageHeading } from "./ui";
const steps = [
  "Identify the issue",
  "Review the evidence",
  "Work through checks",
  "Log the outcome",
];
const symptoms = [
  { label: "Unusual spindle vibration", icon: Activity },
  { label: "Overheating", icon: Thermometer },
  { label: "Unusual noise", icon: Volume2 },
  { label: "Error code", icon: CircleAlert },
  { label: "Tooling issue", icon: Wrench },
  { label: "Something else", icon: HelpCircle },
];
export function Troubleshooting() {
  const params = useSearchParams();
  const initialMachine = params.get("machine");
  const { addRecord } = useKnowledge();
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [machine, setMachine] = useState(
    machines.some((m) => m.id === initialMachine) ? initialMachine! : "CNC-01",
  );
  const [symptom, setSymptom] = useState("Unusual spindle vibration");
  const [context, setContext] = useState("");
  const [step, setStep] = useState(0);
  const [checks, setChecks] = useState<boolean[]>([false, false, false]);
  const [outcome, setOutcome] = useState("Escalated for inspection");
  const [notes, setNotes] = useState("");
  const [feedback, setFeedback] = useState("");
  const [saved, setSaved] = useState("");
  const [answer, setAnswer] = useState<TroubleshootingAnswer | null>(null);
  const [asking, setAsking] = useState(false);
  const [answerError, setAnswerError] = useState("");
  const [failureExecution, setFailureExecution] = useState<AIExecution | null>(
    null,
  );
  const hasEvidence = answer?.status === "answered";
  async function ask() {
    if (asking) return;
    setAnswer(null);
    setAnswerError("");
    setFailureExecution(null);
    setAsking(true);
    setStep(1);
    try {
      const question =
        symptom === "Something else"
          ? context
          : `${symptom}. ${context || "What does approved evidence recommend checking?"}`;
      setAnswer(await askTroubleshooting(machine, question));
    } catch (error) {
      setAnswerError((error as Error).message);
      if (error instanceof ApiError)
        setFailureExecution(error.execution || null);
    } finally {
      setAsking(false);
    }
  }
  async function save(e: React.FormEvent) {
    e.preventDefault();
    if (notes.trim().length < 10 || !feedback) {
      setFormError(
        "Add at least 10 non-padding characters of handover notes and select feedback.",
      );
      return;
    }
    if (saving) return;
    setSaving(true);
    setFormError("");
    try {
      setSaved(
        await addRecord({
          title: `${machine}: ${symptom} — ${outcome}`,
          machineId: machine,
          symptom,
          kind: "Resolution",
          content: `SYNTHETIC TROUBLESHOOTING OUTCOME\n\nSymptom: ${symptom}\nContext: ${context || "Not provided"}\nOutcome: ${outcome}\nTechnician notes: ${notes.trim()}\nEvidence feedback: ${feedback}\n\nThis record is a synthetic demonstration and requires human review.`,
        }),
      );
    } catch (error) {
      setFormError((error as Error).message);
    } finally {
      setSaving(false);
    }
  }
  if (saved)
    return (
      <>
        <PageHeading
          eyebrow="GUIDED TROUBLESHOOTING"
          title="The next shift starts here."
          description="Your outcome adds context for the team that follows."
        />
        <section className="panel success-state">
          <CheckCircle2 size={48} />
          <h2>Outcome logged for review</h2>
          <p>
            {machine} · {outcome}
          </p>
          <span className="mono">{saved}</span>
          <div className="info-box">
            <ShieldCheck size={19} />
            <p>
              This pending record is saved locally. It does not change machine
              status or authorize operation.
            </p>
          </div>
          <div className="button-group">
            <Link href="/approvals" className="button primary">
              Review submission
              <ArrowRight size={16} />
            </Link>
            <button
              className="button secondary"
              onClick={() => {
                setSaved("");
                setStep(0);
                setChecks([false, false, false]);
                setNotes("");
                setContext("");
                setFeedback("");
              }}
            >
              Start another case
            </button>
          </div>
        </section>
      </>
    );
  return (
    <>
      <PageHeading
        eyebrow="GUIDED TROUBLESHOOTING"
        title="A steady path from issue to insight."
        description="Bring machine context and approved knowledge into one focused workflow."
      />
      <DemoNotice>
        AI-assisted workflow · AMD selects passages from approved synthetic
        records. SHIFT verifies citations and source approval. No live machine
        connection.
      </DemoNotice>
      <div className="troubleshoot-layout">
        <aside className="workflow-sidebar">
          <div className="eyebrow">YOUR WORKFLOW</div>
          <ol className="stepper">
            {steps.map((s, i) => (
              <li
                key={s}
                className={step === i ? "current" : step > i ? "complete" : ""}
                aria-current={step === i ? "step" : undefined}
              >
                <span>{step > i ? <Check size={15} /> : i + 1}</span>
                <div>
                  <strong>{s}</strong>
                  <small>
                    {
                      [
                        "Machine & symptoms",
                        "Approved source evidence",
                        "Record your observations",
                        "Share what you learned",
                      ][i]
                    }
                  </small>
                </div>
              </li>
            ))}
          </ol>
          <div className="workflow-context">
            <span className="eyebrow">CURRENT MACHINE</span>
            <strong>{machine}</strong>
            <p>{machines.find((m) => m.id === machine)?.name}</p>
            <span>{machines.find((m) => m.id === machine)?.area}</span>
          </div>
          <div className="quiet-note">
            <ShieldCheck size={18} />
            Decision support only. Qualified personnel and approved site
            procedures govern real maintenance.
          </div>
        </aside>
        <section className="panel workflow-main">
          <div className="workflow-topline">
            <span className="eyebrow">
              STEP {String(step + 1).padStart(2, "0")} OF 04
            </span>
            <Badge tone="info">Evidence-based workflow</Badge>
          </div>
          {step === 0 && (
            <>
              <h2>What issue are you facing?</h2>
              <p className="section-description">
                Choose a machine and the symptom that best matches your
                observation.
              </p>
              <label>
                Machine
                <select
                  value={machine}
                  onChange={(e) => {
                    setMachine(e.target.value);
                    setChecks([false, false, false]);
                  }}
                >
                  {machines.map((m) => (
                    <option key={m.id} value={m.id}>
                      {m.id} — {m.name}
                    </option>
                  ))}
                </select>
              </label>
              <div className="field-heading">Observed symptom</div>
              <div className="symptom-grid">
                {symptoms.map(({ label, icon: Icon }) => (
                  <button
                    key={label}
                    className={`symptom-card ${symptom === label ? "selected" : ""}`}
                    aria-pressed={symptom === label}
                    onClick={() => {
                      setSymptom(label);
                      setChecks([false, false, false]);
                    }}
                  >
                    <Icon size={24} />
                    <span>{label}</span>
                    {symptom === label && (
                      <CheckCircle2 size={15} className="selected-check" />
                    )}
                  </button>
                ))}
              </div>
              <label>
                Additional context{" "}
                <span className="field-hint">
                  {symptom === "Something else"
                    ? "Required · at least 5 characters"
                    : "Optional"}
                </span>
                <textarea
                  maxLength={1400}
                  rows={3}
                  value={context}
                  onChange={(e) => setContext(e.target.value)}
                  placeholder="When did it start? What changed? Describe what you observed."
                />
              </label>
              <div className="info-box">
                <Sparkles size={18} />
                <p>
                  Start with <strong>CNC-01 · Unusual spindle vibration</strong>
                  , or ask about approved evidence for another machine.
                  Unsupported questions produce an insufficient-evidence
                  response.
                </p>
              </div>
            </>
          )}
          {step === 1 && (
            <>
              <h2>Start with what we know.</h2>
              <p className="section-description">
                {machine} <ChevronRight size={13} /> {symptom}
              </p>
              <GroundedAnswer
                failureExecution={failureExecution}
                answer={answer}
                loading={asking}
                error={answerError}
                retry={() => void ask()}
              />
            </>
          )}
          {step === 2 && (
            <>
              <h2>Observe. Document. Escalate.</h2>
              <p className="section-description">
                Use this demo checklist to rehearse the workflow. No physical
                maintenance is requested.
              </p>
              <div className="safety-callout">
                <ShieldCheck size={23} />
                <div>
                  <strong>Safety comes before inspection</strong>
                  <p>
                    For real equipment, qualified personnel must follow
                    site-approved shutdown and lockout/tagout procedures. This
                    synthetic checklist is not a service manual.
                  </p>
                </div>
              </div>
              <div className="checks-list">
                <ChecklistItem
                  checked={checks[0]}
                  onChange={() =>
                    setChecks((c) => c.map((v, i) => (i === 0 ? !v : v)))
                  }
                >
                  <strong>Review the safety requirement</strong>
                  <span>
                    Acknowledge that the site procedure and qualified review
                    govern any real inspection.
                  </span>
                </ChecklistItem>
                <ChecklistItem
                  checked={checks[1]}
                  onChange={() =>
                    setChecks((c) => c.map((v, i) => (i === 1 ? !v : v)))
                  }
                >
                  <strong>Review the example observations</strong>
                  <span>
                    Consider tooling changes, lubrication history, and reported
                    noise. Keep causes unconfirmed.
                  </span>
                </ChecklistItem>
                <ChecklistItem
                  checked={checks[2]}
                  onChange={() =>
                    setChecks((c) => c.map((v, i) => (i === 2 ? !v : v)))
                  }
                >
                  <strong>Prepare a handover</strong>
                  <span>
                    Record findings and any need for supervisor escalation. Do
                    not infer machine clearance.
                  </span>
                </ChecklistItem>
              </div>
              <div className="progress-caption">
                {checks.filter(Boolean).length} of 3 demo checks acknowledged
              </div>
            </>
          )}
          {step === 3 && (
            <form id="resolution-form" onSubmit={save}>
              <h2>What should the next shift know?</h2>
              <p className="section-description">
                Capture the outcome and keep the learning available for review.
              </p>
              <label>
                Demo outcome
                <select
                  value={outcome}
                  onChange={(e) => setOutcome(e.target.value)}
                >
                  {[
                    "Escalated for inspection",
                    "More information needed",
                    "Resolved in demo scenario",
                  ].map((o) => (
                    <option key={o}>{o}</option>
                  ))}
                </select>
              </label>
              <label>
                Resolution or handover notes
                <textarea
                  required
                  minLength={10}
                  maxLength={5000}
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  rows={6}
                  placeholder="What did you learn? What remains unconfirmed? What should the supervisor review?"
                />
              </label>
              <p className="form-error" role="alert">
                {formError}
              </p>
              <fieldset className="feedback-field">
                <legend>Was this evidence useful?</legend>
                {["Helpful", "Needs improvement"].map((f) => (
                  <label key={f}>
                    <input
                      type="radio"
                      name="feedback"
                      required
                      value={f}
                      checked={feedback === f}
                      onChange={() => setFeedback(f)}
                    />
                    {f}
                  </label>
                ))}
              </fieldset>
              <div className="info-box">
                <ClipboardCheck size={18} />
                <p>
                  Your outcome is saved as a pending knowledge submission. A
                  supervisor must review it before it appears in the demo
                  library.
                </p>
              </div>
            </form>
          )}
          <div className="workflow-footer">
            {step > 0 ? (
              <button
                className="button secondary"
                disabled={asking}
                onClick={() => {
                  setStep((s) => s - 1);
                  if (step === 1) setAnswer(null);
                }}
              >
                <ArrowLeft size={16} />
                Back
              </button>
            ) : (
              <Link href="/" className="button secondary">
                <ArrowLeft size={16} />
                Overview
              </Link>
            )}
            <span className="small-text muted">{step + 1} / 4</span>
            {step < 3 ? (
              <button
                className="button primary"
                disabled={
                  asking ||
                  (step === 0 &&
                    symptom === "Something else" &&
                    context.trim().length < 5) ||
                  (step === 1 && !hasEvidence) ||
                  (step === 2 && !checks.every(Boolean))
                }
                onClick={() => {
                  if (step === 0) void ask();
                  else setStep((s) => s + 1);
                }}
              >
                {step === 0
                  ? "Review evidence"
                  : step === 1
                    ? "Continue to checks"
                    : "Log outcome"}
                <ArrowRight size={16} />
              </button>
            ) : (
              <button
                type="submit"
                disabled={saving}
                form="resolution-form"
                className="button primary"
              >
                <FileText size={16} />
                Submit outcome
              </button>
            )}
          </div>
        </section>
      </div>
    </>
  );
}
