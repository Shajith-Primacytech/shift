"use client";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  useState,
  useEffect,
  useRef,
  useSyncExternalStore,
  type ReactNode,
} from "react";
import {
  LayoutDashboard,
  Cpu,
  Sparkles,
  BookOpen,
  ClipboardCheck,
  Plus,
  Search,
  Bell,
  ArrowUpRight,
  Factory,
  Menu,
  X,
  Mic,
  ShieldCheck,
} from "lucide-react";
import { useKnowledge } from "./knowledge-provider";
import { ShiftBrand } from "./shift-brand";
import { ShiftLogo } from "./shift-logo";
import { BackendStatus } from "./backend-status";
const nav = [
  { href: "/", label: "Overview", icon: LayoutDashboard },
  { href: "/machines", label: "Machines", icon: Cpu },
  { href: "/troubleshoot", label: "Troubleshoot", icon: Sparkles },
  { href: "/knowledge", label: "Knowledge library", icon: BookOpen },
  { href: "/approvals", label: "Approvals", icon: ClipboardCheck },
];
function subscribeMobile(callback: () => void) {
  const media = window.matchMedia("(max-width: 760px)");
  media.addEventListener("change", callback);
  return () => media.removeEventListener("change", callback);
}
export function AppShell({ children }: { children: ReactNode }) {
  const path = usePathname();
  const router = useRouter();
  const { records, user, logout } = useKnowledge();
  const [open, setOpen] = useState(false);
  const [search, setSearch] = useState("");
  const sidebarRef = useRef<HTMLElement>(null);
  const isMobile = useSyncExternalStore(
    subscribeMobile,
    () => window.matchMedia("(max-width: 760px)").matches,
    () => false,
  );
  useEffect(() => {
    if (!open || !isMobile) return;
    const previous = document.activeElement as HTMLElement | null;
    const sidebar = sidebarRef.current;
    const controls = () =>
      Array.from(
        sidebar?.querySelectorAll<HTMLElement>(
          "a[href],button:not([disabled])",
        ) || [],
      ).filter((el) => el.getClientRects().length);
    controls()[0]?.focus();
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setOpen(false);
        return;
      }
      if (event.key !== "Tab") return;
      const list = controls();
      const first = list[0];
      const last = list[list.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last?.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first?.focus();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      document.body.style.overflow = previousOverflow;
      previous?.focus();
    };
  }, [open, isMobile]);
  const pending = records.filter((r) => r.status === "Pending").length;
  const active = (href: string) =>
    href === "/" ? path === "/" : path.startsWith(href);
  return (
    <div className="app-shell">
      <a className="skip-link" href="#main">
        Skip to content
      </a>
      {open && (
        <button
          className="sidebar-backdrop"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        />
      )}
      <aside
        ref={sidebarRef}
        inert={isMobile && !open}
        className={`sidebar ${open ? "open" : ""}`}
        aria-label="Main navigation"
      >
        <button
          className="icon-button sidebar-close"
          aria-label="Close menu"
          onClick={() => setOpen(false)}
        >
          <X size={20} />
        </button>
        <Link href="/" className="brand" onClick={() => setOpen(false)}>
          <ShiftBrand />
        </Link>
        <div className="workspace-label">INDUSTRIAL KNOWLEDGE INTELLIGENCE</div>
        <div className="plant-card">
          <span className="plant-icon">
            <Factory size={19} />
          </span>
          <div>
            <strong>Northline Manufacturing</strong>
            <span>Demo facility · Plant 01</span>
          </div>
        </div>
        <div className="nav-caption">WORKSPACE</div>
        <nav>
          {nav.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              onClick={() => setOpen(false)}
              aria-current={active(href) ? "page" : undefined}
              className={`nav-item ${active(href) ? "active" : ""}`}
            >
              <Icon size={19} />
              <span>{label}</span>
              {href === "/approvals" && pending > 0 && (
                <span className="nav-count">{pending}</span>
              )}
              {href === "/troubleshoot" && <span className="nav-ai">AI</span>}
            </Link>
          ))}
        </nav>
        <div className="sidebar-capture">
          <div className="capture-mini-icon">
            <Mic size={20} />
          </div>
          <strong>Experience worth keeping.</strong>
          <p>Turn today’s observations into tomorrow’s answers.</p>
          <Link
            href="/knowledge/capture"
            className="button secondary small-button"
            onClick={() => setOpen(false)}
          >
            <Plus size={16} />
            Capture knowledge
            <ArrowUpRight size={14} />
          </Link>
        </div>
        <div className="sidebar-bottom">
          <div className="demo-mode">
            <span className="status-dot online" /> DEMO WORKSPACE
          </div>
          <div className="user-card">
            <div className="avatar">{user.name.slice(0, 2).toUpperCase()}</div>
            <div>
              <strong>{user.name}</strong>
              <span>{user.role}</span>
            </div>
            <ShieldCheck size={17} />
            <button
              className="button secondary small-button"
              onClick={() => void logout()}
            >
              Sign out
            </button>
          </div>
        </div>
      </aside>
      <div className="main-shell" inert={isMobile && open}>
        <header className="topbar">
          <button
            className="icon-button mobile-menu"
            onClick={() => setOpen(!open)}
            aria-label={open ? "Close navigation" : "Open navigation"}
            aria-expanded={open}
          >
            {open ? <X size={22} /> : <Menu size={22} />}
          </button>
          <div className="breadcrumb">
            Workspace <span>/</span>{" "}
            <strong>
              {path === "/knowledge/capture"
                ? "Capture knowledge"
                : nav.find((n) => active(n.href))?.label || "Overview"}
            </strong>
          </div>
          <form
            className="global-search"
            onSubmit={(e) => {
              e.preventDefault();
              router.push(`/knowledge?q=${encodeURIComponent(search)}`);
            }}
          >
            <Search size={16} />
            <input
              aria-label="Search knowledge"
              placeholder="Search knowledge, symptoms…"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <kbd>↵</kbd>
          </form>
          <Link
            href="/approvals"
            className="icon-button notifications"
            aria-label={`${pending} pending reviews`}
          >
            <Bell size={20} />
            {pending > 0 && <i />}
          </Link>
          <div className="topbar-divider" />
          <span className="shift-label">Shift A</span>
          <div className="avatar top-avatar">
            {user.name.slice(0, 2).toUpperCase()}
          </div>
        </header>
        <main id="main" tabIndex={-1}>
          {children}
        </main>
        <footer className="app-footer">
          <span className="footer-brand">
            <ShiftLogo variant="footer" />
            <span className="muted">/</span> The Memory of the Factory Floor
          </span>
          <BackendStatus />
        </footer>
      </div>
      <nav
        inert={isMobile && open}
        className="mobile-bottom"
        aria-label="Mobile quick navigation"
      >
        {nav.slice(0, 4).map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={active(href) ? "active" : ""}
            aria-current={active(href) ? "page" : undefined}
          >
            <Icon size={20} />
            <span>{label === "Knowledge library" ? "Knowledge" : label}</span>
          </Link>
        ))}
      </nav>
    </div>
  );
}
