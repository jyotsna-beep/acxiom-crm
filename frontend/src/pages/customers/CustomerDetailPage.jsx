import React, { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { getCustomer, getCustomerHistory } from "../../api/customers";
import AlertMessage from "../../components/common/AlertMessage";
import EmptyState from "../../components/common/EmptyState";
import LoadingState from "../../components/common/LoadingState";
import PageHeader from "../../components/common/PageHeader";
import StatusBadge from "../../components/common/StatusBadge";

export default function CustomerDetailPage() {
  const { customerId } = useParams();
  const [customer, setCustomer] = useState(null);
  const [history, setHistory] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => { getCustomer(customerId).then(setCustomer).catch((requestError) => setError(requestError.response?.data?.detail ?? "Unable to load customer.")); getCustomerHistory(customerId).then(setHistory).catch(() => setHistory([])); }, [customerId]);
  if (error) return <AlertMessage>{error}</AlertMessage>;
  if (!customer || history === null) return <LoadingState />;
  return <><PageHeader title={customer.name} description={customer.customer_code} actions={<Link className="btn btn-outline-primary" to={`/customers/${customer.id}/edit`}>Edit customer</Link>} /><div className="row g-4"><div className="col-lg-7"><section className="card"><div className="card-body"><dl className="row mb-0"><dt className="col-sm-4">Email</dt><dd className="col-sm-8">{customer.email}</dd><dt className="col-sm-4">Phone</dt><dd className="col-sm-8">{customer.phone}</dd><dt className="col-sm-4">Status</dt><dd className="col-sm-8"><StatusBadge status={customer.status} /></dd><dt className="col-sm-4">Owner</dt><dd className="col-sm-8">{customer.owner?.username ?? customer.owner?.email ?? "—"}</dd><dt className="col-sm-4">Address</dt><dd className="col-sm-8">{customer.address || "—"}</dd><dt className="col-sm-4">Notes</dt><dd className="col-sm-8 text-break">{customer.notes || "—"}</dd></dl></div></section></div><div className="col-lg-5"><section className="card"><div className="card-body"><h2 className="h5">Customer history</h2>{history.length ? <ul className="list-group list-group-flush">{history.map((entry) => <li className="list-group-item px-0" key={entry.id}><strong>{entry.action.replaceAll("_", " ")}</strong><br /><small className="text-muted">{new Date(entry.created_at).toLocaleString()}</small></li>)}</ul> : <EmptyState title="No history yet" />}</div></section></div></div></>;
}
