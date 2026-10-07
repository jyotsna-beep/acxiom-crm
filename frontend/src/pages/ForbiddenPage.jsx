import { Link } from "react-router-dom";

export default function ForbiddenPage() {
  return <main className="container py-5"><h1 className="h2">Access denied</h1><Link to="/app">Return</Link></main>;
}
