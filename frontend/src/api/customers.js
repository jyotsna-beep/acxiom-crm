import { apiClient } from "./client";

export async function getCustomers(params) {
  const { data } = await apiClient.get("/api/customers", { params });
  return data;
}

export async function getCustomer(customerId) {
  const { data } = await apiClient.get(`/api/customers/${customerId}`);
  return data;
}

export async function getCustomerOwners() {
  const { data } = await apiClient.get("/api/customers/owners");
  return data;
}

export async function getCustomerHistory(customerId) {
  const { data } = await apiClient.get(`/api/customers/${customerId}/history`);
  return data;
}

export async function createCustomer(payload) {
  const { data } = await apiClient.post("/api/customers", payload);
  return data;
}

export async function updateCustomer(customerId, payload) {
  const { data } = await apiClient.put(`/api/customers/${customerId}`, payload);
  return data;
}

export function deactivateCustomer(customerId) {
  return apiClient.delete(`/api/customers/${customerId}`);
}
