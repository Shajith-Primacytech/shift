export type MachineStatus = "Running" | "Attention" | "Maintenance";
export type Machine = {
  id: string;
  name: string;
  area: string;
  category: string;
  status: MachineStatus;
  temperature: number;
  rpm: number;
  vibration: number;
  utilization: number;
  note: string;
};
export const machines: Machine[] = [
  {
    id: "CNC-01",
    name: "Mazak VCN-530C",
    area: "Plant Floor A",
    category: "CNC machining",
    status: "Running",
    temperature: 42,
    rpm: 2400,
    vibration: 0.8,
    utilization: 94,
    note: "Routine inspection completed",
  },
  {
    id: "CNC-02",
    name: "Haas VF-2",
    area: "Plant Floor A",
    category: "CNC machining",
    status: "Attention",
    temperature: 58,
    rpm: 1800,
    vibration: 2.1,
    utilization: 78,
    note: "Vibration inspection requested",
  },
  {
    id: "PRESS-01",
    name: "Hydraulic Press H-200",
    area: "Plant Floor B",
    category: "Forming",
    status: "Running",
    temperature: 38,
    rpm: 0,
    vibration: 0.4,
    utilization: 89,
    note: "Pressure check completed",
  },
  {
    id: "ASSY-01",
    name: "Assembly Line Alpha",
    area: "Plant Floor B",
    category: "Assembly",
    status: "Running",
    temperature: 32,
    rpm: 120,
    vibration: 0.3,
    utilization: 96,
    note: "Shift handover complete",
  },
  {
    id: "COMP-01",
    name: "Atlas Copco GA 22",
    area: "Utilities",
    category: "Air systems",
    status: "Maintenance",
    temperature: 25,
    rpm: 0,
    vibration: 0,
    utilization: 0,
    note: "Scheduled filter replacement",
  },
  {
    id: "CNC-03",
    name: "DMG MORI CMX 600",
    area: "Plant Floor A",
    category: "CNC machining",
    status: "Running",
    temperature: 40,
    rpm: 2100,
    vibration: 0.6,
    utilization: 91,
    note: "Tool inspection completed",
  },
];
export type Attachment = {
  name: string;
  size: number;
  type: string;
  file?: Blob;
  id?: string;
  url?: string;
};
export type KnowledgeRecord = {
  id: string;
  versionId?: string;
  revision?: number;
  title: string;
  machineId: string;
  symptom: string;
  content: string;
  status: "Approved" | "Pending" | "Rejected" | "Revoked";
  kind: "SOP" | "Field note" | "Resolution";
  author: string;
  date: string;
  reviewer?: string;
  reviewNote?: string;
  reviewedAt?: string;
  attachments?: Attachment[];
};
