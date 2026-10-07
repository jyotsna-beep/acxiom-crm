export default function PageHeader({ title, description, actions }) {
  return (
    <header className="d-flex flex-column flex-sm-row justify-content-between align-items-sm-start gap-3 mb-4">
      <div>
        <h1 className="h3 mb-1">{title}</h1>
        {description && <p className="text-muted mb-0">{description}</p>}
      </div>
      {actions && <div className="d-flex gap-2">{actions}</div>}
    </header>
  );
}
