export default function LoadingState({ message = "Loading…" }) {
  return <div className="py-5 text-center text-muted" role="status"><span className="spinner-border spinner-border-sm me-2" aria-hidden="true" />{message}</div>;
}
