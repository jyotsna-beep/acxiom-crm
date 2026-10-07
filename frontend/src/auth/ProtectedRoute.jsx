import React from "react";
import { Navigate, Outlet, useLocation } from "react-router-dom";

import { useAuth } from "./AuthProvider";
import LoadingState from "../components/common/LoadingState";

export default function ProtectedRoute({ allowedRoles }) {
  const { user, isLoading } = useAuth();
  const location = useLocation();

  if (isLoading) {
    return <main className="container py-5"><LoadingState /></main>;
  }
  if (!user) {
    return <Navigate to="/login" replace state={{ from: location }} />;
  }
  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to="/forbidden" replace />;
  }
  return <Outlet />;
}
