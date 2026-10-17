"use client";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import {
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  FileText,
  Mic,
  ShieldCheck,
  Upload,
  X,
} from "lucide-react";
import { machines, type Attachment } from "@/lib/demo-data";
import { useKnowledge } from "./knowledge-provider";
import { DemoNotice, PageHeading } from "./ui";
import { VoiceRecorder } from "./voice-recorder";
export function KnowledgeCapture() {
  const params = useSearchParams();
  const initialMachine = params.get("machine");
  const { addRecord, user } = useKnowledge();
  const [saving, setSaving] = useState(false);
  const [formError, setFormError] = useState("");
  const [recordingBusy, setRecordingBusy] = useState(false);
  const [mode, setMode] = useState("Write");
  const [machine, setMachine] = useState(
    machines.some((m) => m.id === initialMachine) ? initialMachine! : "CNC-01",
  );
  const [title, setTitle] = useState("");
  const [symptom, setSymptom] = useState("");
  const [content, setContent] = useState("");
  const author = user.name;
  const [files, setFiles] = useState<Attachment[]>([]);
  const [audio, setAudio] = useState<Attachment | null>(null);
  const [fileError, setFileError] = useState("");
  const [submitted, setSubmitted] = useState("");
  async function submit(e: FormEvent) {
    e.preventDefault();
    if (recordingBusy || saving) return;
    if (
      !title.trim() ||
      !symptom.trim() ||
      content.trim().length < 10 ||
      !author.trim()
    ) {
      setFormError(
        "Enter a title, symptom, technician name, and an observation of at least 10 non-padding characters.",
      );
      return;
    }
    setSaving(true);
    setFormError("");
    try {
      const id = await addRecord({
        title: title.trim(),
        machineId: machine,
        symptom: symptom.trim(),
        content: content.trim(),
        kind: "Field note",
        attachments: [...files, ...(audio ? [audio] : [])],
      });
      setSubmitted(id);
    } catch (error) {
      setFormError((error as Error).message);
    } finally {
      setSaving(false);
    }
  }
  if (submitted)
    return (
      <>
        <PageHeading
          eyebrow="KNOWLEDGE CAPTURE"
          title="An observation worth keeping."
          description="Your experience is ready for a second pair of eyes."
        />
        <section className="panel success-state">
          <CheckCircle2 size={48} />
          <h2>Saved for supervisor review</h2>
          <p>{title}</p>
          <span className="mono">{submitted}</span>
          <div className="info-box">
            <ShieldCheck size={19} />
            <p>
              This submission is pending and excluded from trusted knowledge. It
              is saved with its attachments and remains available after refresh.
            </p>
          </div>
          <div className="button-group">
            <Link href="/approvals" className="button primary">
              Open review queue
              <ArrowRight size={16} />
            </Link>
            <button
              className="button secondary"
              onClick={() => {
                setSubmitted("");
                setTitle("");
                setSymptom("");
                setContent("");
                setFiles([]);
                setAudio(null);
                setMode("Write");
              }}
            >
              Capture another
            </button>
          </div>
        </section>
      </>
    );
  return (
    <>
      <Link className="back-link" href="/knowledge">
        <ArrowLeft size={15} />
        Knowledge library
      </Link>
      <PageHeading
        eyebrow="KEEP THE KNOW-HOW"
        title="What did you notice?"
        description="Small observations today. Better decisions on the next shift."
      />
      <DemoNotice>
        Persistent local capture · Submissions and source files are saved by the
        SHIFT backend. Only approved knowledge enters the library.
      </DemoNotice>
      <div className="capture-layout">
        <form className="panel capture-form" onSubmit={submit}>
          <div className="section-heading">
            <h2>Capture an observation</h2>
            <span className="step-caption">01 / CAPTURE</span>
          </div>
          <div
            className="capture-modes"
            role="tablist"
            aria-label="Capture method"
          >
            {[
              { label: "Write", icon: FileText },
              { label: "Voice", icon: Mic },
              { label: "Documents", icon: Upload },
            ].map(({ label, icon: Icon }) => (
              <button
                type="button"
                role="tab"
                aria-selected={mode === label}
                aria-controls={`capture-${label}`}
                key={label}
                className={mode === label ? "active" : ""}
                onClick={() => setMode(label)}
              >
                <Icon size={17} />
                {label}
              </button>
            ))}
          </div>
          <div className="form-grid">
            <label>
              Machine
              <select
                value={machine}
                onChange={(e) => setMachine(e.target.value)}
              >
                {machines.map((m) => (
                  <option key={m.id} value={m.id}>
                    {m.id} — {m.name}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Technician name
              <input required maxLength={80} value={author} readOnly />
            </label>
          </div>
          <label>
            Observation title
            <input
              required
              maxLength={140}
              placeholder="e.g. Vibration after a tooling changeover"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />
          </label>
          <label>
            Symptom or maintenance context
            <input
              required
              maxLength={200}
              placeholder="What brought this to your attention?"
              value={symptom}
              onChange={(e) => setSymptom(e.target.value)}
            />
          </label>
          <div id="capture-Voice" hidden={mode !== "Voice"} role="tabpanel">
            <VoiceRecorder
              onChange={setAudio}
              onBusyChange={setRecordingBusy}
            />
          </div>
          <div
            id="capture-Documents"
            hidden={mode !== "Documents"}
            role="tabpanel"
          >
            <label className="upload-zone">
              <Upload size={28} />
              <strong>Select supporting files</strong>
              <span>
                PDF, TXT, Markdown, or audio · up to 10 MB each · 3 files
                maximum
              </span>
              <input
                type="file"
                accept=".pdf,.txt,.md,.webm,.wav,.mp3,.m4a,.ogg,.mp4"
                multiple
                onChange={(e) => {
                  const incoming = Array.from(e.target.files || []);
                  const valid = incoming.filter(
                    (f) =>
                      f.size <= 10 * 1024 * 1024 &&
                      (/\.(pdf|txt|md|webm|wav|mp3|m4a|ogg|mp4)$/i.test(
                        f.name,
                      ) ||
                        f.type.startsWith("audio/")),
                  );
                  if (
                    incoming.length !== valid.length ||
                    files.length + valid.length > 3
                  ) {
                    setFileError(
                      "Choose up to 3 PDF, TXT, Markdown, or audio files, each 10 MB or smaller.",
                    );
                    e.target.value = "";
                    return;
                  }
                  setFiles((current) => [
                    ...current,
                    ...valid.map((f) => ({
                      name: f.name,
                      size: f.size,
                      type: f.type,
                      file: f,
                    })),
                  ]);
                  setFileError("");
                  e.target.value = "";
                }}
              />
            </label>
            <p className="small-text muted">
              Files are saved with the submission for reviewer download. Text
              extraction is not implemented.
            </p>
            {fileError && (
              <p role="alert" className="form-error">
                {fileError}
              </p>
            )}
          </div>
          {files.map((f, i) => (
            <div className="file-row" key={`${f.name}-${i}`}>
              <FileText size={16} />
              <span>{f.name}</span>
              <small>{Math.ceil(f.size / 1024)} KB</small>
              <button
                type="button"
                className="icon-button"
                aria-label={`Remove ${f.name}`}
                onClick={() =>
                  setFiles((current) => current.filter((_, j) => i !== j))
                }
              >
                <X size={16} />
              </button>
            </div>
          ))}
          {audio && (
            <p className="green-text small-text">
              <CheckCircle2 size={14} /> Voice recording attached
            </p>
          )}
          <label id="capture-Write">
            Written observation{" "}
            <span className="field-hint">
              Required for review, including voice and document submissions
            </span>
            <textarea
              required
              minLength={10}
              maxLength={8000}
              rows={6}
              placeholder="Describe what you observed, the operating context, and any action already taken. Separate observations from assumptions."
              value={content}
              onChange={(e) => setContent(e.target.value)}
            />
          </label>
          <div role="alert" className="form-error">
            {formError}
          </div>
          <div className="form-footer">
            <span>
              <ShieldCheck size={15} />
              Human review required
            </span>
            <button
              className="button primary"
              type="submit"
              disabled={recordingBusy || saving}
            >
              {saving
                ? "Saving…"
                : recordingBusy
                  ? "Finish recording first"
                  : "Submit for review"}
              <ArrowRight size={16} />
            </button>
          </div>
        </form>
        <aside className="capture-aside">
          <section className="panel">
            <div className="document-icon">
              <ShieldCheck size={23} />
            </div>
            <h2>Good knowledge starts with context.</h2>
            <p>
              You don’t need to know the answer. A clear observation is a
              valuable starting point.
            </p>
            <ol className="tips-list">
              <li>
                <strong>Describe what you saw</strong>
                <span>Include when it happened and the machine involved.</span>
              </li>
              <li>
                <strong>Keep facts and guesses separate</strong>
                <span>An unconfirmed cause should stay a hypothesis.</span>
              </li>
              <li>
                <strong>Let the team review</strong>
                <span>
                  Only approved entries appear in the trusted demo library.
                </span>
              </li>
            </ol>
          </section>
          <div className="quiet-note">
            Synthetic data only. Do not include confidential factory information
            or credentials.
          </div>
        </aside>
      </div>
    </>
  );
}
