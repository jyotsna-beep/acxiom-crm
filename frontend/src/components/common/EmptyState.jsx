import React from "react";
export default function EmptyState({ title = "Nothing to show", message }) {
  return (
    <section className="border rounded-3 p-4 text-center bg-light" aria-live="polite">
      <h2 className="h5">{title}</h2>
      {message && <p className="text-muted mb-0">{message}</p>}
    </section>
  );
}
