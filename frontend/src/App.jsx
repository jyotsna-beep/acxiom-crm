import { Navigate, Route, Routes } from "react-router-dom";

import ProtectedRoute from "./auth/ProtectedRoute";
import ForbiddenPage from "./pages/ForbiddenPage";
import LoginPage from "./pages/LoginPage";
import AppLayout from "./layouts/AppLayout";
import DashboardPlaceholderPage from "./pages/DashboardPlaceholderPage";
import ModulePlaceholderPage from "./pages/ModulePlaceholderPage";
import CustomerCreatePage from "./pages/customers/CustomerCreatePage";
import CustomerDetailPage from "./pages/customers/CustomerDetailPage";
import CustomerEditPage from "./pages/customers/CustomerEditPage";
import CustomerListPage from "./pages/customers/CustomerListPage";
import LeadListPage from "./pages/leads/LeadListPage";
import LeadCreatePage from "./pages/leads/LeadCreatePage";
import LeadDetailPage from "./pages/leads/LeadDetailPage";
import LeadEditPage from "./pages/leads/LeadEditPage";
import NotFoundPage from "./pages/NotFoundPage";
import RegisterPage from "./pages/RegisterPage";

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/register" element={<RegisterPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route path="/dashboard" element={<DashboardPlaceholderPage />} />
          <Route path="/customers" element={<CustomerListPage />} />
          <Route path="/customers/new" element={<CustomerCreatePage />} />
          <Route path="/customers/:customerId" element={<CustomerDetailPage />} />
          <Route path="/customers/:customerId/edit" element={<CustomerEditPage />} />
          <Route path="/leads" element={<LeadListPage />} />
          <Route path="/leads/new" element={<LeadCreatePage />} />
          <Route path="/leads/:leadId" element={<LeadDetailPage />} />
          <Route path="/leads/:leadId/edit" element={<LeadEditPage />} />
          <Route path="/follow-ups" element={<ModulePlaceholderPage title="Follow-Ups" />} />
          <Route path="/opportunities" element={<ModulePlaceholderPage title="Opportunities" />} />
          <Route path="/activities" element={<ModulePlaceholderPage title="Activities" />} />
          <Route path="/reports" element={<ModulePlaceholderPage title="Reports" />} />
          <Route element={<ProtectedRoute allowedRoles={["Admin"]} />}>
            <Route path="/users" element={<ModulePlaceholderPage title="Users" />} />
            <Route path="/audit-logs" element={<ModulePlaceholderPage title="Audit Logs" />} />
          </Route>
          <Route path="/forbidden" element={<ForbiddenPage />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
