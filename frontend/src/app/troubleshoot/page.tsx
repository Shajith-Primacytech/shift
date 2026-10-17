import { Suspense } from "react";
import { Troubleshooting } from "@/components/troubleshooting";
export default function TroubleshootPage() {
  return (
    <Suspense fallback={<p role="status">Loading guided workflow…</p>}>
      <Troubleshooting />
    </Suspense>
  );
}
