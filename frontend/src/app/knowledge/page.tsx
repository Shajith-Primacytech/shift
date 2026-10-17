import { Suspense } from "react";
import { KnowledgeLibrary } from "@/components/knowledge-library";
export default async function KnowledgePage({
  searchParams,
}: {
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const params = await searchParams;
  return (
    <Suspense fallback={<p role="status">Loading knowledge…</p>}>
      <KnowledgeLibrary key={JSON.stringify(params)} />
    </Suspense>
  );
}
