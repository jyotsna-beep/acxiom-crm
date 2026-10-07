import React from "react";
import EmptyState from "../components/common/EmptyState";
import PageHeader from "../components/common/PageHeader";

export default function DashboardPlaceholderPage() {
  return <><PageHeader title="Dashboard" description="Your authorized CRM summary will appear here." /><EmptyState title="Dashboard coming next" message="No dashboard analytics have been implemented in this phase." /></>;
}
