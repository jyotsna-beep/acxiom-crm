import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";

import { apiClient, establishPublicCsrfToken } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    apiClient
      .get("/api/auth/me")
      .then(({ data }) => setUser(data))
      .catch(() => setUser(null))
      .finally(() => setIsLoading(false));
  }, []);

  const login = useCallback(async (credentials) => {
    await establishPublicCsrfToken();
    const { data } = await apiClient.post("/api/auth/login", credentials);
    setUser(data.user);
    return data.user;
  }, []);

  const register = useCallback(async (registration) => {
    await establishPublicCsrfToken();
    return apiClient.post("/api/auth/register", registration);
  }, []);

  const logout = useCallback(async () => {
    await apiClient.post("/api/auth/logout");
    setUser(null);
  }, []);

  const value = useMemo(() => ({ user, isLoading, login, logout, register }), [user, isLoading, login, logout, register]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within AuthProvider.");
  }
  return context;
}
