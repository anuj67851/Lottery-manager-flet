ADMIN_ROLE = "admin"
EMPLOYEE_ROLE = "employee"
SALESPERSON_ROLE = "salesperson"

ALL_USER_ROLES = [ADMIN_ROLE, EMPLOYEE_ROLE, SALESPERSON_ROLE]
# Roles that can be typically managed (created/edited by an admin/salesperson)
MANAGED_USER_ROLES = [ADMIN_ROLE, EMPLOYEE_ROLE]


# Route Names
LOGIN_ROUTE = "login"
ADMIN_DASHBOARD_ROUTE = "admin_dashboard"
EMPLOYEE_DASHBOARD_ROUTE = "employee_dashboard"
SALESPERSON_DASHBOARD_ROUTE = "salesperson_dashboard"