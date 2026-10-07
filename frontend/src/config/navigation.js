const roles = {
  admin: ["Admin"],
  management: ["Admin", "Manager"],
  all: ["Admin", "Manager", "Sales Executive"],
};

export const navigationItems = [
  { label: "Dashboard", to: "/dashboard", roles: roles.all },
  { label: "Customers", to: "/customers", roles: roles.all },
  { label: "Leads", to: "/leads", roles: roles.all },
  { label: "Follow-Ups", to: "/follow-ups", roles: roles.all },
  { label: "Opportunities", to: "/opportunities", roles: roles.all },
  { label: "Activities", to: "/activities", roles: roles.all },
  { label: "Users", to: "/users", roles: roles.admin },
  { label: "Audit Logs", to: "/audit-logs", roles: roles.admin },
  { label: "Reports", to: "/reports", roles: roles.all },
];

export function visibleNavigationItems(role) {
  return navigationItems.filter((item) => item.roles.includes(role));
}
