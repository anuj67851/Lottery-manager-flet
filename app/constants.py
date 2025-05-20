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
MIN_REQUIRED_SCAN_LENGTH = GAME_LENGTH + BOOK_LENGTH
MIN_REQUIRED_SCAN_LENGTH_WITH_TICKET = GAME_LENGTH + BOOK_LENGTH + TICKET_LENGTH

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

# User Management (Admin Specific)
ADMIN_USER_MANAGEMENT_ROUTE = "admin_user_management"

# Book Action Dialog Types (used for configuration)
BOOK_ACTION_ADD_NEW = "add_new"
BOOK_ACTION_FULL_SALE = "full_sale"
BOOK_ACTION_ACTIVATE = "activate"

# Report Routes (Admin Specific)
SALES_BY_DATE_REPORT_ROUTE = "sales_by_date_report"
# Placeholders for other reports - can be expanded later
BOOK_OPEN_REPORT_ROUTE = "book_open_report"
GAME_EXPIRY_REPORT_ROUTE = "game_expiry_report"
STOCK_LEVELS_REPORT_ROUTE = "stock_levels_report"