"use client";
import { useEffect, useRef } from "react";
import { Download, FileText } from "lucide-react";
import type { Attachment } from "@/lib/demo-data";
export function AudioPreview({ blob }: { blob: Blob }) {
  const ref = useRef<HTMLAudioElement>(null);
  useEffect(() => {
    const url = URL.createObjectURL(blob);
    const audio = ref.current;
    if (audio) audio.src = url;
    return () => {
      if (audio) audio.removeAttribute("src");
      URL.revokeObjectURL(url);
    };
  }, [blob]);
  return <audio ref={ref} controls aria-label="Recorded observation" />;
}
export function AttachmentPreview({ attachment }: { attachment: Attachment }) {
  const ref = useRef<HTMLAnchorElement>(null);
  useEffect(() => {
    const url = attachment.file
      ? URL.createObjectURL(attachment.file)
      : attachment.url;
    if (!url) return;
    if (ref.current) ref.current.href = url;
    return () => {
      if (attachment.file) URL.revokeObjectURL(url);
    };
  }, [attachment.file, attachment.url]);
  return (
    <div className="attachment-preview">
      <div>
        <FileText size={17} />
        <span>
          {attachment.name}{" "}
          <small>({Math.ceil(attachment.size / 1024)} KB)</small>
        </span>
        <a
          ref={ref}
          download={attachment.name}
          className="icon-button"
          aria-label={`Download ${attachment.name}`}
        >
          <Download size={16} />
        </a>
      </div>
      {attachment.type.startsWith("audio/") &&
        attachment.url &&
        !attachment.file && (
          <audio
            controls
            src={attachment.url}
            aria-label="Recorded observation"
          />
        )}
      {attachment.type.startsWith("audio/") && attachment.file && (
        <AudioPreview blob={attachment.file} />
      )}
    </div>
  );
}
