import Link from "next/link";
export default function NotFound() {
  return (
    <div className="empty-state">
      <h1>We couldn’t find that page.</h1>
      <p>Choose a machine or return to your workspace.</p>
      <Link className="button primary" href="/">
        Back to overview
      </Link>
    </div>
  );
}
