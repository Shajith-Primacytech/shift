"use client";
import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
  type FormEvent,
} from "react";
import type { KnowledgeRecord } from "@/lib/demo-data";
import {
  api,
  apiBase,
  ApiError,
  jsonRequest,
  knowledgeApi,
  type NewKnowledge,
  type User,
} from "@/lib/api";
import { ShiftBrand } from "./shift-brand";

type KnowledgeContextValue = {
  user: User;
  records: KnowledgeRecord[];
  addRecord: (record: NewKnowledge) => Promise<string>;
  review: (
    id: string,
    status: "Approved" | "Rejected" | "Revoked",
    note: string,
  ) => Promise<void>;
  refresh: () => Promise<void>;
  logout: () => Promise<void>;
};
const KnowledgeContext = createContext<KnowledgeContextValue | null>(null);
export function KnowledgeProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [records, setRecords] = useState<KnowledgeRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    const [approved, submissions] = await Promise.all([
      knowledgeApi.approved(),
      knowledgeApi.submissions(),
    ]);
    const merged = new Map([...approved, ...submissions].map((r) => [r.id, r]));
    setRecords(
      [...merged.values()].map((r) => ({
        ...r,
        attachments: r.attachments?.map((a) => ({
          ...a,
          url: `${apiBase()}/api/v1/documents/${a.id}`,
        })),
      })),
    );
  }, []);
  const initialize = useCallback(() => {
    return api<User>("/auth/me")
      .then(async (current) => {
        await refresh();
        setUser(current);
        setError("");
      })
      .catch((e: unknown) => {
        setUser(null);
        setRecords([]);
        if (!(e instanceof ApiError && e.status === 401))
          setError((e as Error).message);
      })
      .finally(() => setLoading(false));
  }, [refresh]);
  useEffect(() => {
    void initialize();
  }, [initialize]);
  // Refresh when switching back from a supervisor/technician browser session.
  useEffect(() => {
    const onFocus = () => {
      if (user) void initialize();
    };
    window.addEventListener("focus", onFocus);
    return () => window.removeEventListener("focus", onFocus);
  }, [user, refresh, initialize]);
  async function signIn(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const current = await api<User>(
        "/auth/login",
        jsonRequest({ username, password }),
      );
      await refresh();
      setUser(current);
      setError("");
      setPassword("");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function addRecord(record: NewKnowledge) {
    const result = await knowledgeApi.submit(record);
    // Mutation success is distinct from a refresh failure: never invite duplicate submissions.
    setRecords((current) => [
      {
        ...result,
        attachments: result.attachments?.map((a) => ({
          ...a,
          url: `${apiBase()}/api/v1/documents/${a.id}`,
        })),
      },
      ...current.filter((r) => r.id !== result.id),
    ]);
    return result.id;
  }
  async function review(
    id: string,
    status: "Approved" | "Rejected" | "Revoked",
    note: string,
  ) {
    const record = records.find((r) => r.id === id);
    if (!record)
      throw new Error("Submission no longer available. Refresh the queue.");
    const result = await knowledgeApi.review(record, status, note);
    setRecords((current) =>
      current.map((r) =>
        r.id === id
          ? {
              ...result,
              attachments: result.attachments?.map((a) => ({
                ...a,
                url: `${apiBase()}/api/v1/documents/${a.id}`,
              })),
            }
          : r,
      ),
    );
  }
  async function logout() {
    try {
      await api("/auth/logout", { method: "POST" });
      setUser(null);
      setRecords([]);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  if (loading)
    return (
      <main className="auth-page">
        <p role="status">Opening SHIFT workspace…</p>
      </main>
    );
  if (!user)
    return (
      <main className="auth-page">
        <form className="panel auth-card" onSubmit={signIn}>
          <div className="brand">
            <ShiftBrand />
          </div>
          <h1>Welcome to your shift.</h1>
          <p className="muted">
            Sign in to capture knowledge and review approved sources. All
            factory data is synthetic.
          </p>
          <label>
            Username
            <input
              autoComplete="username"
              required
              maxLength={100}
              value={username}
              onChange={(e) => setUsername(e.target.value)}
            />
          </label>
          <label>
            Password
            <input
              type="password"
              autoComplete="current-password"
              required
              maxLength={256}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          {error && (
            <p role="alert" className="form-error">
              {error}
            </p>
          )}
          <button className="button primary" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
          <button
            type="button"
            className="button secondary"
            disabled={busy}
            onClick={() => void initialize()}
          >
            Retry connection
          </button>
          <p className="small-text muted">
            Accounts are provisioned by your local SHIFT administrator.
            Knowledge and review decisions are saved on this computer.
          </p>
        </form>
      </main>
    );
  return (
    <KnowledgeContext.Provider
      value={{ user, records, addRecord, review, refresh, logout }}
    >
      {error && (
        <div role="alert" className="form-error">
          {error}
        </div>
      )}
      {children}
    </KnowledgeContext.Provider>
  );
}
export function useKnowledge() {
  const value = useContext(KnowledgeContext);
  if (!value) throw new Error("KnowledgeProvider is required");
  return value;
}
