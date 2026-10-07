import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { createCustomer, getCustomerOwners } from "../../api/customers";
import CustomerForm from "../../components/customers/CustomerForm";
import EmptyState from "../../components/common/EmptyState";
import LoadingState from "../../components/common/LoadingState";
import PageHeader from "../../components/common/PageHeader";

export default function CustomerCreatePage() {
  const navigate = useNavigate();
  const [owners, setOwners] = useState(null);

  useEffect(() => { getCustomerOwners().then(setOwners).catch(() => setOwners([])); }, []);
  if (owners === null) return <LoadingState />;
  if (!owners.length) return <><PageHeader title="Create customer" /><EmptyState title="No available owner" message="An active permitted owner is required before a customer can be created." /></>;

  return <><PageHeader title="Create customer" description="Customer ownership is enforced by the server." /><CustomerForm owners={owners} submitLabel="Create customer" onSubmit={async (payload) => { const customer = await createCustomer(payload); navigate(`/customers/${customer.id}`); }} /></>;
}
