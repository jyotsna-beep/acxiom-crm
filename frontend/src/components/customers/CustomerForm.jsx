import React, { useEffect, useState } from "react";

import AlertMessage from "../common/AlertMessage";

const emptyForm = { name: "", email: "", phone: "", address: "", status: "active", notes: "", owner_id: "" };

export default function CustomerForm({ initialCustomer, owners, onSubmit, submitLabel }) {
  const [form, setForm] = useState(emptyForm);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (initialCustomer) {
      setForm({
        name: initialCustomer.name,
        email: initialCustomer.email,
        phone: initialCustomer.phone,
        address: initialCustomer.address ?? "",
        status: initialCustomer.status,
        notes: initialCustomer.notes ?? "",
        owner_id: initialCustomer.owner?.id ?? "",
      });
    }
  }, [initialCustomer]);

  function update(field) {
    return (event) => setForm((current) => ({ ...current, [field]: event.target.value }));
  }

  async function submit(event) {
    event.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await onSubmit({
        ...form,
        address: form.address || null,
        notes: form.notes || null,
        owner_id: form.owner_id || null,
      });
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "Unable to save the customer.");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate>
      {error && <AlertMessage>{error}</AlertMessage>}
      <div className="row g-3">
        <div className="col-md-6"><label className="form-label" htmlFor="customer-name">Name</label><input className="form-control" id="customer-name" value={form.name} onChange={update("name")} required maxLength="150" /></div>
        <div className="col-md-6"><label className="form-label" htmlFor="customer-email">Email</label><input className="form-control" id="customer-email" type="email" value={form.email} onChange={update("email")} required maxLength="254" /></div>
        <div className="col-md-6"><label className="form-label" htmlFor="customer-phone">Phone</label><input className="form-control" id="customer-phone" type="tel" value={form.phone} onChange={update("phone")} required maxLength="32" aria-describedby="phone-help" /><div className="form-text" id="phone-help">Use 7–15 digits; spaces and punctuation are normalized.</div></div>
        <div className="col-md-6"><label className="form-label" htmlFor="customer-owner">Owner</label><select className="form-select" id="customer-owner" value={form.owner_id} onChange={update("owner_id")} required><option value="">Select an owner</option>{owners.map((owner) => <option key={owner.id} value={owner.id}>{owner.username ?? owner.email}</option>)}</select></div>
        <div className="col-md-6"><label className="form-label" htmlFor="customer-status">Status</label><select className="form-select" id="customer-status" value={form.status} onChange={update("status")}><option value="active">Active</option><option value="inactive">Inactive</option></select></div>
        <div className="col-12"><label className="form-label" htmlFor="customer-address">Address</label><textarea className="form-control" id="customer-address" rows="3" value={form.address} onChange={update("address")} maxLength="500" /></div>
        <div className="col-12"><label className="form-label" htmlFor="customer-notes">Notes</label><textarea className="form-control" id="customer-notes" rows="4" value={form.notes} onChange={update("notes")} maxLength="2000" /></div>
      </div>
      <div className="mt-4"><button className="btn btn-primary" type="submit" disabled={submitting}>{submitting ? "Saving…" : submitLabel}</button></div>
    </form>
  );
}
