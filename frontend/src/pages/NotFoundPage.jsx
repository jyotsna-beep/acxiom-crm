import { Link } from "react-router-dom";

export default function NotFoundPage() {
  return (
    <main className="container py-5">
      <h1 className="h2">Page not found</h1>
      <Link to="/">Return to AcxiomCRM</Link>
    </main>
  );
}
