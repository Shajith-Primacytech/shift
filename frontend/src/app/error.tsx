"use client";
export default function ErrorPage({ reset }: { reset: () => void }) {
  return (
    <div className="empty-state">
      <h1>Something interrupted this view.</h1>
      <p>Your session may still be available. Try opening the view again.</p>
      <button className="button primary" onClick={reset}>
        Try again
      </button>
    </div>
  );
}
