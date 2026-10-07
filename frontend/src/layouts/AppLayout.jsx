import React, { useState } from "react";
import { NavLink, Outlet } from "react-router-dom";

import AlertMessage from "../components/common/AlertMessage";
import { visibleNavigationItems } from "../config/navigation";
import { useAuth } from "../auth/AuthProvider";

export default function AppLayout() {
  const { logout, user } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);
  const [error, setError] = useState("");
  const navigation = visibleNavigationItems(user.role);

  async function handleLogout() {
    setError("");
    try {
      await logout();
    } catch {
      setError("Unable to sign out. Please try again.");
    }
  }

  return (
    <div className="min-vh-100 bg-body-tertiary">
      <header className="navbar navbar-dark bg-primary px-3 sticky-top">
        <button className="btn btn-primary d-lg-none me-2" type="button" aria-label="Toggle navigation" aria-expanded={menuOpen} onClick={() => setMenuOpen((open) => !open)}>☰</button>
        <span className="navbar-brand mb-0 h1">AcxiomCRM</span>
        <div className="ms-auto d-flex align-items-center gap-3 text-white small">
          <span className="d-none d-sm-inline text-end"><strong className="d-block">{user.username ?? user.email}</strong><span>{user.role}</span></span>
          <button className="btn btn-sm btn-outline-light" type="button" onClick={handleLogout}>Logout</button>
        </div>
      </header>
      <div className="container-fluid">
        <div className="row">
          <aside className={`col-lg-2 px-0 bg-white border-end shell-sidebar ${menuOpen ? "d-block" : "d-none d-lg-block"}`}>
            <nav className="nav flex-column p-3" aria-label="Primary navigation">
              {navigation.map((item) => <NavLink key={item.to} className={({ isActive }) => `nav-link rounded mb-1 ${isActive ? "active bg-primary text-white" : "text-dark"}`} to={item.to} onClick={() => setMenuOpen(false)}>{item.label}</NavLink>)}
            </nav>
          </aside>
          <main className="col-lg-10 py-4 px-md-4">
            {error && <AlertMessage onDismiss={() => setError("")}>{error}</AlertMessage>}
            <Outlet />
          </main>
        </div>
      </div>
    </div>
  );
}
