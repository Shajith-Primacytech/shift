"use client";
import { useState } from "react";
import { Search, Cpu } from "lucide-react";
import { machines } from "@/lib/demo-data";
import { MachineCard } from "@/components/machine-card";
import { DemoNotice, EmptyState, PageHeading } from "@/components/ui";
export default function MachinesPage() {
  const [query, setQuery] = useState("");
  const [status, setStatus] = useState("All statuses");
  const [area, setArea] = useState("All areas");
  const filtered = machines.filter(
    (m) =>
      `${m.id} ${m.name} ${m.category}`
        .toLowerCase()
        .includes(query.toLowerCase()) &&
      (status === "All statuses" || m.status === status) &&
      (area === "All areas" || m.area === area),
  );
  return (
    <>
      <PageHeading
        eyebrow="ASSET WORKSPACE"
        title="Know your machines."
        description="One place for machine context, observations, and maintenance knowledge."
      />
      <DemoNotice />
      <div className="filter-bar">
        <div className="input-with-icon">
          <Search size={18} />
          <input
            aria-label="Search machines"
            placeholder="Search by machine ID, model, or type…"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
          />
        </div>
        <select
          aria-label="Filter by status"
          value={status}
          onChange={(e) => setStatus(e.target.value)}
        >
          {["All statuses", "Running", "Attention", "Maintenance"].map((s) => (
            <option key={s}>{s}</option>
          ))}
        </select>
        <select
          aria-label="Filter by area"
          value={area}
          onChange={(e) => setArea(e.target.value)}
        >
          {["All areas", "Plant Floor A", "Plant Floor B", "Utilities"].map(
            (s) => (
              <option key={s}>{s}</option>
            ),
          )}
        </select>
      </div>
      <div className="results-label" role="status">
        {filtered.length} machines <span>· Synthetic telemetry snapshot</span>
      </div>
      {filtered.length ? (
        <div className="machine-grid">
          {filtered.map((m) => (
            <MachineCard key={m.id} machine={m} />
          ))}
        </div>
      ) : (
        <EmptyState icon={Cpu} title="No matching machines">
          Try a different machine ID, status, or production area.
        </EmptyState>
      )}
    </>
  );
}
