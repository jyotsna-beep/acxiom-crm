import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [identity, setIdentity] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login({ identity, password });
      navigate(location.state?.from?.pathname ?? "/app", { replace: true });
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "Unable to sign in.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="container py-5" style={{ maxWidth: "28rem" }}>
      <h1 className="h2 mb-4">Sign in to AcxiomCRM</h1>
      {error && <div className="alert alert-danger" role="alert">{error}</div>}
      <form onSubmit={submit} noValidate>
        <label className="form-label" htmlFor="identity">Email or username</label>
        <input className="form-control mb-3" id="identity" value={identity} onChange={(event) => setIdentity(event.target.value)} required autoComplete="username" />
        <label className="form-label" htmlFor="password">Password</label>
        <input className="form-control mb-3" id="password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} required autoComplete="current-password" />
        <button className="btn btn-primary w-100" disabled={submitting} type="submit">{submitting ? "Signing in…" : "Sign in"}</button>
      </form>
      <p className="mt-3 mb-0">Need an account? <Link to="/register">Register</Link></p>
    </main>
  );
}
