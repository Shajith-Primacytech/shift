import Link from "next/link";
import { ArrowUpRight, Thermometer, Activity, Gauge, Cpu } from "lucide-react";
import { type Machine } from "@/lib/demo-data";
import { StatusBadge } from "./ui";
export function MachineCard({ machine }: { machine: Machine }) {
  return (
    <Link href={`/machines/${machine.id}`} className="machine-card">
      <div className="machine-card-top">
        <span className="machine-icon">
          <Cpu size={22} />
        </span>
        <StatusBadge status={machine.status} />
      </div>
      <div className="machine-card-title">
        <div>
          <h3>{machine.id}</h3>
          <p>{machine.name}</p>
        </div>
        <ArrowUpRight size={18} />
      </div>
      <span className="machine-area">
        {machine.area} <span>·</span> {machine.category}
      </span>
      <div className="machine-card-metrics">
        <span>
          <Thermometer size={14} />
          <strong>{machine.temperature}°C</strong>
        </span>
        <span>
          <Gauge size={14} />
          <strong>
            {machine.rpm.toLocaleString("en-US")} <small>rpm</small>
          </strong>
        </span>
        <span>
          <Activity size={14} />
          <strong>
            {machine.vibration} <small>mm/s</small>
          </strong>
        </span>
      </div>
      <div className="machine-card-bottom">
        <span
          className={`status-dot ${machine.status === "Running" ? "online" : "offline"}`}
        />
        {machine.note}
      </div>
    </Link>
  );
}
