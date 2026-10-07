import { useAuth } from "../auth/AuthProvider";

export default function AuthFoundationPage() {
  const { logout, user } = useAuth();
  return (
    <main className="container py-5">
      <h1 className="h2">AcxiomCRM</h1>
      <p>Signed in as {user.name} ({user.role}).</p>
      <button className="btn btn-outline-secondary" type="button" onClick={logout}>Sign out</button>
    </main>
  );
}
