"use client";
import { useEffect, useRef, useState } from "react";
import { Mic, Square, Trash2 } from "lucide-react";
import type { Attachment } from "@/lib/demo-data";
import { AudioPreview } from "./attachment-preview";
export function VoiceRecorder({
  onChange,
  onBusyChange,
}: {
  onChange: (attachment: Attachment | null) => void;
  onBusyChange: (busy: boolean) => void;
}) {
  const recorder = useRef<MediaRecorder | null>(null);
  const stream = useRef<MediaStream | null>(null);
  const mounted = useRef(true);
  const chunks = useRef<Blob[]>([]);
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [recording, setRecording] = useState(false);
  const [requesting, setRequesting] = useState(false);
  const [error, setError] = useState("");
  const [audio, setAudio] = useState<Blob | null>(null);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
      if (timer.current) clearTimeout(timer.current);
      if (recorder.current?.state === "recording") recorder.current.stop();
      stream.current?.getTracks().forEach((t) => t.stop());
    };
  }, []);
  async function start() {
    setError("");
    if (
      !navigator.mediaDevices?.getUserMedia ||
      typeof MediaRecorder === "undefined"
    ) {
      setError(
        "Recording is unavailable in this browser. Use written observations or attach an audio file. Microphone access requires localhost or HTTPS.",
      );
      return;
    }
    setRequesting(true);
    onBusyChange(true);
    try {
      const nextStream = await navigator.mediaDevices.getUserMedia({
        audio: true,
      });
      if (!mounted.current) {
        nextStream.getTracks().forEach((t) => t.stop());
        return;
      }
      stream.current = nextStream;
      const next = new MediaRecorder(nextStream);
      recorder.current = next;
      chunks.current = [];
      next.ondataavailable = (e) => {
        if (e.data.size) chunks.current.push(e.data);
      };
      next.onstop = () => {
        if (timer.current) clearTimeout(timer.current);
        nextStream.getTracks().forEach((t) => t.stop());
        if (!mounted.current) return;
        const blob = new Blob(chunks.current, {
          type: next.mimeType || "audio/webm",
        });
        setRecording(false);
        onBusyChange(false);
        if (!blob.size || blob.size > 10 * 1024 * 1024) {
          setError(
            "Recording is empty or larger than 10 MB. Please try a shorter recording.",
          );
          return;
        }
        setAudio(blob);
        onChange({
          name: `voice-observation.${next.mimeType.includes("mp4") ? "m4a" : "webm"}`,
          file: blob,
          size: blob.size,
          type: blob.type,
        });
      };
      next.onerror = () => {
        nextStream.getTracks().forEach((t) => t.stop());
        if (mounted.current) {
          setError(
            "Recording was interrupted. Please retry or write your observation.",
          );
          setRecording(false);
          onBusyChange(false);
        }
      };
      next.start();
      setAudio(null);
      onChange(null);
      setRecording(true);
      timer.current = setTimeout(() => {
        if (next.state === "recording") next.stop();
      }, 120000);
    } catch {
      stream.current?.getTracks().forEach((t) => t.stop());
      if (mounted.current) {
        setError(
          "Microphone access was denied or no microphone is available. You can still submit written observations.",
        );
        onBusyChange(false);
      }
    } finally {
      if (mounted.current) setRequesting(false);
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
        Audio is saved when you submit. No transcription. Maximum 2 minutes.
      </p>
      <button
        type="button"
        className={`button ${recording ? "danger" : "secondary"}`}
        disabled={requesting}
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
          ? "Stop the recording before submitting your observation."
          : ""}
      </p>
      {audio && (
        <div className="recording-preview">
          <AudioPreview blob={audio} />
          <button
            type="button"
            className="icon-button"
            aria-label="Remove recording"
            onClick={() => {
              setAudio(null);
              onChange(null);
            }}
          >
            <Trash2 size={17} />
          </button>
        </div>
      )}
      {error && (
        <p className="form-error" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
