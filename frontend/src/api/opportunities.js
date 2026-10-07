import { apiClient } from "./client";
export const getOpportunities=(params)=>apiClient.get("/api/opportunities",{params}).then((r)=>r.data);
export const getOpportunity=(id)=>apiClient.get(`/api/opportunities/${id}`).then((r)=>r.data);
export const getOpportunityOwners=()=>apiClient.get("/api/opportunities/owners").then((r)=>r.data);
export const createOpportunity=(payload)=>apiClient.post("/api/opportunities",payload).then((r)=>r.data);
export const updateOpportunity=(id,payload)=>apiClient.put(`/api/opportunities/${id}`,payload).then((r)=>r.data);
export const changeOpportunityStage=(id,stage)=>apiClient.post(`/api/opportunities/${id}/stage`,{stage}).then((r)=>r.data);
export const getOpportunityHistory=(id)=>apiClient.get(`/api/opportunities/${id}/history`).then((r)=>r.data);
