import { apiClient } from "./client";

export async function getLeads(params) { return (await apiClient.get("/api/leads", { params })).data; }
export async function getLead(id) { return (await apiClient.get(`/api/leads/${id}`)).data; }
export async function getLeadOwners() { return (await apiClient.get("/api/leads/owners")).data; }
export async function getLeadHistory(id) { return (await apiClient.get(`/api/leads/${id}/history`)).data; }
export async function createLead(payload) { return (await apiClient.post("/api/leads", payload)).data; }
export async function updateLead(id, payload) { return (await apiClient.put(`/api/leads/${id}`, payload)).data; }
export async function changeLeadStatus(id, status) { return (await apiClient.post(`/api/leads/${id}/status`, { status })).data; }
export async function convertLead(id) { return (await apiClient.post(`/api/leads/${id}/convert`)).data; }
