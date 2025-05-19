ADMIN_ROLE = "admin"
EMPLOYEE_ROLE = "employee"
SALESPERSON_ROLE = "salesperson"

ALL_USER_ROLES = [ADMIN_ROLE, EMPLOYEE_ROLE, SALESPERSON_ROLE]
# Roles that can be typically managed (created/edited by an admin/salesperson)
MANAGED_USER_ROLES = [ADMIN_ROLE, EMPLOYEE_ROLE]

# QR code constants
QR_TOTAL_LENGTH = 29
GAME_LENGTH = 3
BOOK_LENGTH = 7
TICKET_LENGTH = 3
MIN_REQUIRED_SCAN_LENGTH = 13

# Ticket orders
REVERSE_TICKET_ORDER = "reverse"
FORWARD_TICKET_ORDER = "forward"

# Route Names
LOGIN_ROUTE = "login"
ADMIN_DASHBOARD_ROUTE = "admin_dashboard"
EMPLOYEE_DASHBOARD_ROUTE = "employee_dashboard"
SALESPERSON_DASHBOARD_ROUTE = "salesperson_dashboard"

# Game Management routes
GAME_MANAGEMENT_ROUTE = "game_management"

# Book management routes
BOOK_MANAGEMENT_ROUTE = "book_management"

# Sales Entry Route
SALES_ENTRY_ROUTE = "sales_entry"
