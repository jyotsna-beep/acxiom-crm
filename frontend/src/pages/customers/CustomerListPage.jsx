import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { deactivateCustomer, getCustomerOwners, getCustomers } from "../../api/customers";
import AlertMessage from "../../components/common/AlertMessage";
import ConfirmDialog from "../../components/common/ConfirmDialog";
import EmptyState from "../../components/common/EmptyState";
import LoadingState from "../../components/common/LoadingState";
import PageHeader from "../../components/common/PageHeader";
import Pagination from "../../components/common/Pagination";
import SearchFilterContainer from "../../components/common/SearchFilterContainer";
import StatusBadge from "../../components/common/StatusBadge";

const initialFilters = { search: "", status: "", owner_id: "", page: 1, page_size: 20, sort_by: "name", sort_order: "asc" };

export default function CustomerListPage() {
  const [filters, setFilters] = useState(initialFilters);
  const [draft, setDraft] = useState(initialFilters);
  const [data, setData] = useState(null);
  const [owners, setOwners] = useState([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);
  const [customerToDeactivate, setCustomerToDeactivate] = useState(null);

  useEffect(() => {
    getCustomerOwners().then(setOwners).catch(() => setOwners([]));
  }, []);

  useEffect(() => {
    setLoading(true);
    setError("");
    const params = Object.fromEntries(Object.entries(filters).filter(([, value]) => value !== "" && value !== null));
    getCustomers(params).then(setData).catch((requestError) => setError(requestError.response?.data?.detail ?? "Unable to load customers.")).finally(() => setLoading(false));
  }, [filters]);

  function updateDraft(field) {
    return (event) => setDraft((current) => ({ ...current, [field]: event.target.value }));
  }

  function applyFilters(event) {
    event.preventDefault();
    setFilters({ ...draft, page: 1 });
  }

  async function confirmDeactivation() {
    try {
      await deactivateCustomer(customerToDeactivate.id);
      setCustomerToDeactivate(null);
      setFilters((current) => ({ ...current }));
    } catch (requestError) {
      setError(requestError.response?.data?.detail ?? "Unable to deactivate this customer.");
      setCustomerToDeactivate(null);
    }
  }

  return (
    <>
      <PageHeader title="Customers" description="Manage customer records within your authorized scope." actions={<Link className="btn btn-primary" to="/customers/new">Create customer</Link>} />
      {error && <AlertMessage onDismiss={() => setError("")}>{error}</AlertMessage>}
      <SearchFilterContainer onSubmit={applyFilters}>
        <div className="row g-3 align-items-end">
          <div className="col-md-4"><label className="form-label" htmlFor="customer-search">Search</label><input className="form-control" id="customer-search" placeholder="Name, email, or phone" value={draft.search} onChange={updateDraft("search")} /></div>
          <div className="col-md-3"><label className="form-label" htmlFor="customer-filter-status">Status</label><select className="form-select" id="customer-filter-status" value={draft.status} onChange={updateDraft("status")}><option value="">All statuses</option><option value="active">Active</option><option value="inactive">Inactive</option></select></div>
          <div className="col-md-3"><label className="form-label" htmlFor="customer-filter-owner">Owner</label><select className="form-select" id="customer-filter-owner" value={draft.owner_id} onChange={updateDraft("owner_id")}><option value="">All permitted owners</option>{owners.map((owner) => <option key={owner.id} value={owner.id}>{owner.username ?? owner.email}</option>)}</select></div>
          <div className="col-md-2"><button className="btn btn-outline-primary w-100" type="submit">Apply</button></div>
        </div>
      </SearchFilterContainer>
      {loading ? <LoadingState message="Loading customers…" /> : data?.items.length ? <div className="card"><div className="table-responsive"><table className="table table-hover mb-0"><thead><tr><th>Code</th><th>Name</th><th>Contact</th><th>Status</th><th>Owner</th><th className="text-end">Actions</th></tr></thead><tbody>{data.items.map((customer) => <tr key={customer.id}><td>{customer.customer_code}</td><td><Link to={`/customers/${customer.id}`}>{customer.name}</Link></td><td><div>{customer.email}</div><small className="text-muted">{customer.phone}</small></td><td><StatusBadge status={customer.status} /></td><td>{customer.owner?.username ?? customer.owner?.email ?? "—"}</td><td className="text-end"><Link className="btn btn-sm btn-outline-secondary me-2" to={`/customers/${customer.id}/edit`}>Edit</Link>{customer.status === "active" && <button className="btn btn-sm btn-outline-danger" type="button" onClick={() => setCustomerToDeactivate(customer)}>Deactivate</button>}</td></tr>)}</tbody></table></div><div className="card-body border-top d-flex justify-content-between align-items-center"><small className="text-muted">{data.total} customer{data.total === 1 ? "" : "s"}</small><Pagination page={data.page} pageCount={data.total_pages} onPageChange={(page) => setFilters((current) => ({ ...current, page }))} /></div></div> : <EmptyState title="No customers found" message="Adjust your filters or create a customer." />}
      <ConfirmDialog isOpen={Boolean(customerToDeactivate)} title="Deactivate customer" message={`Deactivate ${customerToDeactivate?.name ?? "this customer"}? Historical records will be retained.`} confirmLabel="Deactivate" onCancel={() => setCustomerToDeactivate(null)} onConfirm={confirmDeactivation} />
    </>
  );
}
