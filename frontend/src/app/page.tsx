"use client";
import Link from "next/link";
import {
  Activity,
  ArrowRight,
  ArrowUpRight,
  BookOpen,
  CheckCircle2,
  ChevronRight,
  ClipboardCheck,
  Cpu,
  Gauge,
  Plus,
  ShieldCheck,
  Sparkles,
  Thermometer,
  Wrench,
  Clock3,
} from "lucide-react";
import { useKnowledge } from "@/components/knowledge-provider";
import {
  ActionLink,
  Badge,
  DemoNotice,
  PageHeading,
  SectionHeading,
  StatusBadge,
} from "@/components/ui";
import { MachineIllustration } from "@/components/machine-illustration";
import { MachineCard } from "@/components/machine-card";
import { machines } from "@/lib/demo-data";
export default function Dashboard() {
  const { records } = useKnowledge();
  const approved = records.filter((r) => r.status === "Approved");
  const pending = records.filter((r) => r.status === "Pending");
  return (
    <>
      <PageHeading
        eyebrow="PLANT 01 / OPERATIONS OVERVIEW"
        title="A clearer picture. A smarter shift."
        description="Your machines, your team’s knowledge, and the next best step."
        action={
          <Link href="/knowledge/capture" className="button primary">
            <Plus size={17} />
            Capture knowledge
          </Link>
        }
      />
      <DemoNotice />
      <div className="stats-grid">
        <Stat
          icon={Cpu}
          label="Machines on the floor"
          value="06"
          detail="Across 3 production areas"
        />
        <Stat
          icon={Activity}
          label="Running normally"
          value="04"
          detail="2 machines need your attention"
          green
        />
        <Stat
          icon={BookOpen}
          label="Approved knowledge"
          value={String(approved.length).padStart(2, "0")}
          detail="Reviewed. Ready to reference."
        />
        <Stat
          icon={ClipboardCheck}
          label="Awaiting review"
          value={String(pending.length).padStart(2, "0")}
          detail="Keep the knowledge moving"
          amber
        />
      </div>
      <div className="dashboard-main-grid">
        <section className="panel featured-machine">
          <div className="panel-topline">
            <span className="eyebrow">MACHINE SPOTLIGHT</span>
            <Link href="/machines/CNC-01" className="text-link">
              Machine details
              <ArrowUpRight size={15} />
            </Link>
          </div>
          <div className="spotlight-body">
            <div className="spotlight-info">
              <div className="location-label">
                Plant Floor A <ChevronRight size={12} /> CNC machining
              </div>
              <h2>CNC-01</h2>
              <p className="machine-model">Mazak VCN-530C</p>
              <StatusBadge status="Running" />
              <p className="spotlight-description">
                Every observation adds up.
                <br />
                Keep this machine’s knowledge close.
              </p>
              <Link
                href="/troubleshoot?machine=CNC-01"
                className="button primary"
              >
                <Sparkles size={17} />
                Troubleshoot
                <ArrowRight size={16} />
              </Link>
            </div>
            <MachineIllustration />
          </div>
          <div className="spotlight-metrics">
            <Metric
              icon={Thermometer}
              label="Temperature"
              value="42"
              unit="°C"
              caption="Demo reading"
            />
            <Metric
              icon={Gauge}
              label="Spindle speed"
              value="2,400"
              unit="RPM"
              caption="Demo reading"
            />
            <Metric
              icon={Activity}
              label="Vibration"
              value="0.8"
              unit="mm/s"
              caption="Demo reading"
            />
          </div>
        </section>
        <section className="panel floor-panel">
          <div className="section-heading">
            <h2>Factory at a glance</h2>
            <Badge tone="blue">Demo</Badge>
          </div>
          <p className="muted small-text">
            A snapshot of your production floor.
          </p>
          <div className="floor-map" aria-label="Synthetic factory layout">
            <div className="floor-zone zone-a">
              <span>FLOOR A · MACHINING</span>
              <div>
                {machines
                  .filter((m) => m.area === "Plant Floor A")
                  .map((m) => (
                    <Link
                      key={m.id}
                      href={`/machines/${m.id}`}
                      className={`floor-machine ${m.status === "Attention" ? "warning" : ""}`}
                    >
                      <Cpu size={22} />
                      <strong>{m.id}</strong>
                      <span
                        className={`status-dot ${m.status === "Running" ? "online" : "offline"}`}
                      />
                    </Link>
                  ))}
              </div>
            </div>
            <div className="floor-zone zone-b">
              <span>FLOOR B · PRODUCTION</span>
              <div>
                {machines
                  .filter((m) => m.area === "Plant Floor B")
                  .map((m) => (
                    <Link
                      key={m.id}
                      href={`/machines/${m.id}`}
                      className="floor-machine"
                    >
                      <Cpu size={22} />
                      <strong>{m.id}</strong>
                      <span className="status-dot online" />
                    </Link>
                  ))}
              </div>
            </div>
            <div className="floor-zone zone-c">
              <span>UTILITIES</span>
              <Link
                href="/machines/COMP-01"
                className="floor-machine maintenance"
              >
                <Gauge size={22} />
                <strong>COMP-01</strong>
                <span className="status-dot" />
              </Link>
            </div>
          </div>
          <div className="map-legend">
            <span>
              <i className="status-dot online" />
              Running
            </span>
            <span>
              <i className="status-dot offline" />
              Attention
            </span>
            <span>
              <i className="status-dot" />
              Maintenance
            </span>
          </div>
        </section>
      </div>
      <SectionHeading
        title="One step ahead"
        subtitle="The right tools, right when you need them."
      />
      <div className="actions-grid">
        <ActionLink
          href="/troubleshoot"
          icon={Sparkles}
          title="Troubleshoot an issue"
          description="Work through a guided diagnosis"
        />
        <ActionLink
          href="/knowledge/capture"
          icon={Plus}
          title="Capture an observation"
          description="Keep hard-earned knowledge"
        />
        <ActionLink
          href="/knowledge"
          icon={BookOpen}
          title="Find a trusted answer"
          description="Explore approved demo knowledge"
        />
      </div>
      <SectionHeading
        title="On your radar"
        subtitle="A closer look at the machines that keep things moving."
        href="/machines"
        linkText="All machines"
      />
      <div className="machine-grid dashboard-machines">
        {machines.slice(0, 3).map((m) => (
          <MachineCard key={m.id} machine={m} />
        ))}
      </div>
      <div className="dashboard-bottom-grid">
        <section className="panel">
          <SectionHeading
            title="Knowledge, passed forward"
            href="/knowledge"
            linkText="Explore library"
          />
          {approved.slice(0, 3).map((record) => (
            <Link
              key={record.id}
              href={`/knowledge?id=${record.id}`}
              className="knowledge-row"
            >
              <div className="document-icon">
                <BookOpen size={19} />
              </div>
              <div>
                <h3>{record.title}</h3>
                <p>
                  {record.machineId} <span>·</span> {record.kind} <span>·</span>{" "}
                  {record.author}
                </p>
              </div>
              <ShieldCheck size={17} className="green-text" />
              <ChevronRight size={16} />
            </Link>
          ))}
        </section>
        <section className="panel shift-notes">
          <SectionHeading title="Shift handover" />
          <div className="timeline-item">
            <span className="timeline-icon amber">
              <Wrench size={15} />
            </span>
            <div>
              <h3>CNC-02 needs a closer look</h3>
              <p>Vibration inspection requested.</p>
              <Link href="/machines/CNC-02">
                View machine <ArrowRight size={12} />
              </Link>
            </div>
          </div>
          <div className="timeline-item">
            <span className="timeline-icon blue">
              <Clock3 size={15} />
            </span>
            <div>
              <h3>{pending.length} observations awaiting review</h3>
              <p>Help the next shift start informed.</p>
              <Link href="/approvals">
                Open review queue <ArrowRight size={12} />
              </Link>
            </div>
          </div>
          <div className="timeline-item">
            <span className="timeline-icon green">
              <CheckCircle2 size={15} />
            </span>
            <div>
              <h3>Demo shift briefing complete</h3>
              <p>Synthetic snapshot · October 15, 2026</p>
            </div>
          </div>
        </section>
      </div>
    </>
  );
}
function Stat({
  icon: Icon,
  label,
  value,
  detail,
  green,
  amber,
}: {
  icon: typeof Cpu;
  label: string;
  value: string;
  detail: string;
  green?: boolean;
  amber?: boolean;
}) {
  return (
    <div className="stat-card">
      <div className="stat-label">
        {label}
        <Icon
          size={17}
          className={green ? "green-text" : amber ? "amber-text" : "muted"}
        />
      </div>
      <div className="stat-value">
        {value}
        <span
          className={green ? "green-text" : amber ? "amber-text" : "blue-text"}
        >
          {green ? "● Operational" : amber ? "Review queue" : ""}
        </span>
      </div>
      <p>{detail}</p>
    </div>
  );
}
function Metric({
  icon: Icon,
  label,
  value,
  unit,
  caption,
}: {
  icon: typeof Cpu;
  label: string;
  value: string;
  unit: string;
  caption: string;
}) {
  return (
    <div className="metric">
      <span className="metric-icon">
        <Icon size={20} />
      </span>
      <div>
        <span className="metric-label">{label}</span>
        <strong>
          {value} <small>{unit}</small>
        </strong>
        <span className="metric-caption">{caption}</span>
      </div>
    </div>
  );
}
