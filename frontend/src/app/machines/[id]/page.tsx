import { notFound } from "next/navigation";
import { machines } from "@/lib/demo-data";
import { MachineDetail } from "@/components/machine-detail";
export default async function MachinePage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const machine = machines.find((m) => m.id === id);
  if (!machine) notFound();
  return <MachineDetail machine={machine} />;
}
