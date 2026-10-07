import React, { useState } from "react";
import { Link } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";

const emptyForm = { name: "", email: "", username: "", password: "" };

export default function RegisterPage() {
  const { register } = useAuth();
  const [form, setForm] = useState(emptyForm);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  function update(field) {
    return (event) => setForm((current) => ({ ...current, [field]: event.target.value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setSubmitting(true);
    try {
      const { data } = await register({ ...form, username: form.username || null });
      setMessage(data.message);
      setForm(emptyForm);
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "Unable to register.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <main className="container py-5" style={{ maxWidth: "32rem" }}>
      <h1 className="h2 mb-4">Register</h1>
      {message && <div className="alert alert-success" role="alert">{message}</div>}
      {error && <div className="alert alert-danger" role="alert">{error}</div>}
      <form onSubmit={submit} noValidate>
        <label className="form-label" htmlFor="name">Name</label>
        <input className="form-control mb-3" id="name" value={form.name} onChange={update("name")} required autoComplete="name" />
        <label className="form-label" htmlFor="email">Email</label>
        <input className="form-control mb-3" id="email" type="email" value={form.email} onChange={update("email")} required autoComplete="email" />
        <label className="form-label" htmlFor="username">Username (optional)</label>
        <input className="form-control mb-3" id="username" value={form.username} onChange={update("username")} autoComplete="username" />
        <label className="form-label" htmlFor="new-password">Password</label>
        <input className="form-control mb-3" id="new-password" type="password" value={form.password} onChange={update("password")} required minLength="8" autoComplete="new-password" />
        <p className="small text-muted">Use 8+ characters with uppercase, lowercase, number, and special character.</p>
        <button className="btn btn-primary w-100" disabled={submitting} type="submit">{submitting ? "Registering…" : "Register"}</button>
      </form>
      <p className="mt-3 mb-0"><Link to="/login">Back to sign in</Link></p>
    </main>
  );
}
