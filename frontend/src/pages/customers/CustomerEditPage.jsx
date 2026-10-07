import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";

import { getCustomer, getCustomerOwners, updateCustomer } from "../../api/customers";
import CustomerForm from "../../components/customers/CustomerForm";
import AlertMessage from "../../components/common/AlertMessage";
import LoadingState from "../../components/common/LoadingState";
import PageHeader from "../../components/common/PageHeader";

export default function CustomerEditPage() {
  const { customerId } = useParams();
  const navigate = useNavigate();
  const [customer, setCustomer] = useState(null);
  const [owners, setOwners] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => { getCustomer(customerId).then(setCustomer).catch((requestError) => setError(requestError.response?.data?.detail ?? "Unable to load customer.")); getCustomerOwners().then(setOwners).catch(() => setOwners([])); }, [customerId]);
  if (error) return <AlertMessage>{error}</AlertMessage>;
  if (!customer || owners === null) return <LoadingState />;
  return <><PageHeader title={`Edit ${customer.name}`} /><CustomerForm initialCustomer={customer} owners={owners} submitLabel="Save changes" onSubmit={async (payload) => { const updated = await updateCustomer(customerId, payload); navigate(`/customers/${updated.id}`); }} /></>;
}
