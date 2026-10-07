export default function AlertMessage({ children, variant = "danger", onDismiss }) {
  if (!children) {
    return null;
  }
  return (
    <div className={`alert alert-${variant} d-flex justify-content-between align-items-start`} role="alert">
      <span>{children}</span>
      {onDismiss && <button type="button" className="btn-close" aria-label="Dismiss" onClick={onDismiss} />}
    </div>
  );
}
