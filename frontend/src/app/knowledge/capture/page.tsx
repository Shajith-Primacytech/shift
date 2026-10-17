import { Suspense } from "react";
import { KnowledgeCapture } from "@/components/knowledge-capture";
export default function CapturePage() {
  return (
    <Suspense fallback={<p role="status">Loading capture form…</p>}>
      <KnowledgeCapture />
    </Suspense>
  );
}
