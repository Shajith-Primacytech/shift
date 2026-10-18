"use client";
import { useEffect, useRef, useState } from "react";
import { Mic, Square, Trash2 } from "lucide-react";
import type { Attachment } from "@/lib/demo-data";
import {
  transcribeVoice,
  voiceStatus,
  type VoiceStatus,
  type VoiceTranscript,
} from "@/lib/api";
import { AudioPreview } from "./attachment-preview";

function releaseStream(stream: MediaStream | null) {
  stream?.getTracks().forEach((track) => {
    if (track.readyState !== "ended") track.stop();
  });
}

export function VoiceRecorder({
  onChange,
  onBusyChange,
  onUseTranscript,
  active = true,
  disabled = false,
}: {
  onChange: (attachment: Attachment | null) => void;
  onBusyChange: (busy: boolean) => void;
  onUseTranscript?: (text: string) => boolean;
  active?: boolean;
  disabled?: boolean;
}) {
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const mounted = useRef(true);
  const activeRef = useRef(active);
  const acquiring = useRef(false);
  const transcribingRef = useRef(false);
  const abort = useRef<AbortController | null>(null);
  const chunks = useRef<Blob[]>([]);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [recording, setRecording] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [transcribing, setTranscribing] = useState(false);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [audio, setAudio] = useState<Blob | null>(null);
  const [status, setStatus] = useState<VoiceStatus | null>(null);
  const [statusLoaded, setStatusLoaded] = useState(false);
  const [result, setResult] = useState<VoiceTranscript | null>(null);
  const [transcript, setTranscript] = useState("");
  const [used, setUsed] = useState(false);

  useEffect(() => {
    mounted.current = true;
    void voiceStatus()
      .then((value) => {
        if (mounted.current) setStatus(value);
      })
      .catch(() => {})
      .finally(() => {
        if (mounted.current) setStatusLoaded(true);
      });
    const stopWhenHidden = () => {
      if (
        document.visibilityState === "hidden" &&
        recorder.current?.state === "recording"
      ) {
        setMessage(
          "Recording stopped when the page was hidden. Review it before transcription.",
        );
        recorder.current.stop();
      }
    };
    document.addEventListener("visibilitychange", stopWhenHidden);
    return () => {
      mounted.current = false;
      document.removeEventListener("visibilitychange", stopWhenHidden);
      abort.current?.abort();
      if (timer.current) clearTimeout(timer.current);
      if (recorder.current?.state === "recording") recorder.current.stop();
      releaseStream(stream.current);
    };
  }, []);
  useEffect(() => {
    activeRef.current = active;
    if (!active && recorder.current?.state === "recording")
      recorder.current.stop();
  }, [active]);

  async function start() {
    if (acquiring.current || transcribingRef.current || disabled) return;
    setError("");
    setMessage("");
    if (
      !navigator.mediaDevices?.getUserMedia ||
      typeof MediaRecorder === "undefined"
    ) {
      setError(
        "Recording is unavailable in this browser. Use written observations or attach an audio file. Microphone access requires localhost or HTTPS.",
      );
      return;
    }
    acquiring.current = true;
    setRequesting(true);
    onBusyChange(true);
    try {
      const nextStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      if (
        !mounted.current ||
        !activeRef.current ||
        document.visibilityState === "hidden"
      ) {
        if (mounted.current) onBusyChange(false);
        releaseStream(nextStream);
        return;
      }
      stream.current = nextStream;
      const next = new MediaRecorder(nextStream);
      let failed = false;
      recorder.current = next;
      chunks.current = [];
      const fail = () => {
        failed = true;
        if (next.state === "recording") next.stop();
        releaseStream(nextStream);
        if (mounted.current) {
          setError(
            "Recording was interrupted. Please retry or write your observation.",
          );
          setRecording(false);
          onBusyChange(false);
        }
      };
      nextStream
        .getTracks()
        .forEach((track) =>
          track.addEventListener("ended", fail, { once: true }),
        );
      next.ondataavailable = (e) => {
        if (e.data.size) chunks.current.push(e.data);
      };
      next.onstop = () => {
        if (timer.current) clearTimeout(timer.current);
        releaseStream(nextStream);
        if (!mounted.current) return;
        setRecording(false);
        onBusyChange(false);
        if (failed) return;
        const blob = new Blob(chunks.current, {
          type: next.mimeType || "audio/webm",
        });
        if (!blob.size || blob.size > 10 * 1024 * 1024) {
          setError(
            "Recording is empty or larger than 10 MB. Please try a shorter recording.",
          );
          return;
        }
        setAudio(blob);
        onChange({
          name: `voice-observation.${next.mimeType.includes("mp4") ? "m4a" : next.mimeType.includes("ogg") ? "ogg" : "webm"}`,
          file: blob,
          size: blob.size,
          type: blob.type,
        });
      };
      next.onerror = fail;
      next.start();
      setAudio(null);
      setResult(null);
      setTranscript("");
      setUsed(false);
      onChange(null);
      setRecording(true);
      timer.current = setTimeout(() => {
        if (next.state === "recording") {
          setMessage(
            "Two-minute recording limit reached. Review the recording before transcription.",
          );
          next.stop();
        }
      }, 120000);
    } catch (e) {
      releaseStream(stream.current);
      if (mounted.current) {
        const name = (e as { name?: string }).name;
        setError(
          name === "NotAllowedError" || name === "SecurityError"
            ? "Microphone access was denied. You can still submit written observations."
            : name === "NotFoundError" || name === "OverconstrainedError"
              ? "No microphone was detected. Connect a microphone or continue with written observations."
              : "The microphone could not start. Check browser permissions or continue with written observations.",
        );
        onBusyChange(false);
      }
    } finally {
      acquiring.current = false;
      if (mounted.current) setRequesting(false);
    }
  }

  async function transcribe() {
    if (
      !audio ||
      disabled ||
      transcribingRef.current ||
      recording ||
      requesting
    )
      return;
    transcribingRef.current = true;
    setTranscribing(true);
    onBusyChange(true);
    setError("");
    setMessage("");
    const controller = new AbortController();
    abort.current = controller;
    const timeout = setTimeout(() => controller.abort(), 75000);
    try {
      const response = await transcribeVoice(audio, controller.signal);
      if (!mounted.current) return;
      setResult(response);
      setTranscript(response.text);
      setUsed(false);
      setMessage(
        "Transcription ready. Correct any errors, then choose Use Transcript. Nothing has been submitted or sent to Gemma.",
      );
    } catch (e) {
      if (mounted.current)
        setError(
          `${(e as Error).message} Your recording and written observation are unchanged.`,
        );
    } finally {
      clearTimeout(timeout);
      transcribingRef.current = false;
      if (mounted.current) {
        setTranscribing(false);
        onBusyChange(false);
      }
    }
  }

  return (
    <div className="voice-box">
      <div className={`voice-orb ${recording ? "recording" : ""}`}>
        <Mic size={25} />
      </div>
      <h3>
        {recording
          ? "Recording your observation…"
          : "Your experience. In your own words."}
      </h3>
      <p>
        English transcription runs on SHIFT’s local CPU with Whisper tiny.en. No
        audio is sent to AMD or another speech service. Maximum 2 minutes.
      </p>
      <p className="small-text muted">
        Audio is saved only if you submit it as an attachment. Temporary
        transcription files are deleted after processing. Gemma receives only
        the written text you review and choose to use.
      </p>
      <button
        type="button"
        className={`button ${recording ? "danger" : "secondary"}`}
        disabled={requesting || transcribing || disabled}
        onClick={
          recording
            ? () => {
                if (recorder.current?.state === "recording")
                  recorder.current.stop();
              }
            : start
        }
      >
        {recording ? <Square size={16} /> : <Mic size={16} />}{" "}
        {recording
          ? "Stop recording"
          : requesting
            ? "Requesting microphone…"
            : audio
              ? "Record again"
              : "Start recording"}
      </button>
      <p className="small-text" role="status">
        {recording
          ? "Microphone active. Stop the recording before submitting your observation."
          : transcribing
            ? "Transcribing locally… No automatic retries."
            : message}
      </p>
      {audio && (
        <div className="recording-preview">
          <AudioPreview blob={audio} />
          <button
            type="button"
            className="icon-button"
            aria-label="Remove recording"
            disabled={transcribing || disabled}
            onClick={() => {
              setAudio(null);
              setResult(null);
              setTranscript("");
              setUsed(false);
              setError("");
              setMessage("");
              onChange(null);
            }}
          >
            <Trash2 size={17} />
          </button>
        </div>
      )}
      {audio && (
        <div className="button-group">
          {" "}
          <button
            type="button"
            className="button secondary"
            disabled={
              recording ||
              requesting ||
              transcribing ||
              disabled ||
              !status?.available
            }
            onClick={() => void transcribe()}
          >
            {transcribing
              ? "Transcribing…"
              : result
                ? "Transcribe recording again"
                : "Transcribe recording"}
          </button>
        </div>
      )}
      <p className="small-text muted">
        {!statusLoaded
          ? "Checking local transcription availability…"
          : status?.available
            ? "Local English transcription ready."
            : "Local transcription unavailable. Ask your administrator to install the voice extra and prepare the model. Recording and manual capture remain available."}
      </p>
      {result && (
        <>
          <p className="small-text muted">
            {result.provider} · {result.model} ·{" "}
            {(result.latency_ms / 1000).toFixed(2)} s ·{" "}
            {result.duration_seconds.toFixed(1)} s audio
          </p>
          <details className="small-text muted">
            <summary>Original automatic transcript</summary>
            <p>{result.text}</p>
          </details>
          <label>
            Reviewed voice transcript
            <textarea
              rows={4}
              maxLength={8000}
              value={transcript}
              disabled={transcribing || disabled}
              onChange={(e) => {
                setTranscript(e.target.value);
                setUsed(false);
              }}
            />
          </label>
          <p className="small-text muted">
            Use Transcript appends to existing written observations; it does not
            replace them. Check equipment identifiers, fault codes and
            negations.
          </p>
          <button
            type="button"
            className="button secondary"
            disabled={transcribing || disabled || used || !transcript.trim()}
            onClick={() => {
              if (onUseTranscript?.(transcript.trim())) {
                setUsed(true);
                setMessage(
                  "Transcript added to written observation. Review the title and symptom, then choose Structure with AI if wanted.",
                );
              }
            }}
          >
            Use Transcript
          </button>
        </>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
