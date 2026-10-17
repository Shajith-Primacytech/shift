export default function Loading() {
  return (
    <div className="loading-state" role="status">
      <div className="skeleton skeleton-title" />
      <div className="skeleton skeleton-panel" />
      <p>Loading workspace…</p>
    </div>
  );
}
