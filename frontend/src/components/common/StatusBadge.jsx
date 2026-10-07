import React from "react";
const statusVariants = { active: "success", inactive: "secondary", open: "primary", completed: "success", planned: "warning", lost: "danger", won: "success" };

export default function StatusBadge({ status }) {
  const normalizedStatus = String(status ?? "").toLowerCase();
  return <span className={`badge text-bg-${statusVariants[normalizedStatus] ?? "secondary"}`}>{status}</span>;
}
