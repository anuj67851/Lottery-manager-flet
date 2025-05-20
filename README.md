# Lottery Manager (Version 0.1 - Beta)

Lottery Manager is a desktop application built with Python and Flet, designed to help manage lottery game inventory, sales, and reporting for small to medium-sized lottery retail operations.

## Table of Contents

1.  [Overview](#overview)
2.  [Features](#features)
    *   [General](#general)
    *   [Salesperson Role](#salesperson-role)
    *   [Admin Role](#admin-role)
    *   [Employee Role](#employee-role)
3.  [Technology Stack](#technology-stack)
4.  [Prerequisites](#prerequisites)
5.  [Setup and Installation](#setup-and-installation)
6.  [Running the Application](#running-the-application)
7.  [Initial Setup Flow (First Time Use)](#initial-setup-flow-first-time-use)
8.  [Database](#database)
9.  [Key Application Logic](#key-application-logic)
    *   [QR Code Scanning](#qr-code-scanning)
    *   [Book Management](#book-management)
    *   [Shift Submissions](#shift-submissions)
10. [Future Enhancements (Ideas)](#future-enhancements-ideas)
11. [Contributing](#contributing)

## Overview

The Lottery Manager application provides a user-friendly interface for:
*   Tracking lottery game inventory (games and individual books).
*   Recording sales of instant lottery tickets.
*   Managing employee shifts and reconciling daily sales figures.
*   Generating various reports for sales analysis and inventory status.
*   User account management with distinct roles (Salesperson, Admin, Employee).

The application uses a local SQLite database for data persistence and offers features like database backup and license activation (managed by the Salesperson).

## Features

### General
*   **User Authentication:** Secure login for Salesperson, Admin, and Employee roles.
*   **Role-Based Access Control:** Different features and views are available based on the logged-in user's role.
*   **Responsive UI:** Built with Flet, offering a modern Material 3 themed interface.
*   **Light/Dark Mode:** Supports both light and dark themes (configurable).
*   **Data Persistence:** Uses SQLite database to store all application data.
*   **Error Handling:** Custom exceptions and user-friendly error messages.

### Salesperson Role
*   **Initial Setup:**
    *   Creates the first Administrator account.
    *   Activates/Deactivates the application license.
*   **User Management:** Can view, add, and edit Admin and Employee user accounts (excluding Salesperson accounts).
*   **Dashboard:** Access to license and user management functionalities.

### Admin Role
*   **Dashboard:** Central hub for accessing all administrative functions.
*   **Game Management:**
    *   Create new lottery games (defining name, price, total tickets, ticket order, game number).
    *   Edit existing game details (name, game number; price, total tickets, order can be changed if no sales recorded).
    *   Expire active games (marks game and associated active books as finished).
    *   Reactivate expired games.
*   **Book Management:**
    *   Add new books for existing games (manually or via scan).
    *   Edit book details (book number, current ticket; ticket order can be changed if no sales recorded).
    *   Activate/Deactivate individual books.
    *   Delete books (only if inactive and no sales entries).
*   **Sales Functions (Admin Overrides/Tools):**
    *   **Full Book Sale:** Mark one or more entire books as fully sold. This creates a special administrative shift and corresponding sales entries.
    *   **Activate Books (Batch):** Activate multiple scanned/selected books.
*   **Sales Entry & Shift Submission:** Access to the primary sales entry screen for recording daily sales and submitting shifts (can act as an employee).
*   **User Management:**
    *   Manage Admin and Employee accounts (create, edit details, change role between Admin/Employee, activate/deactivate).
    *   Cannot change own role if Admin.
    *   Cannot change another Admin's password.
*   **Reporting:**
    *   **Sales & Shift Submission Report:** Detailed breakdown of sales entries and shift summaries by date range and user.
    *   **Open Books Report:** Lists all currently active books with remaining tickets and value.
    *   **Game Expiry Report:** Shows active and expired games, with filtering options.
    *   **Stock Levels Report:** Summarizes book stock (total, active, finished, pending) per game and calculates active stock value.
    *   All reports can be exported to PDF.
*   **System Management:**
    *   **Database Backup:** Create timestamped backups of the application database.

### Employee Role
*   **Dashboard:** Simple dashboard with access to sales entry.
*   **Sales Entry & Shift Submission:**
    *   Primary interface for recording daily sales.
    *   Enter cumulative daily totals from external terminals (online sales, online payouts, instant payouts).
    *   Scan instant game tickets (Game-Book-Ticket format) to record sales.
    *   Manually enter next ticket number for books.
    *   Confirm "all tickets sold" for a book.
    *   Submit shift at the end of their work period, which finalizes sales entries and calculates deltas and net drop for the shift.

## Technology Stack

*   **GUI Framework:** [Flet](https://flet.dev/) (Python)
*   **Database ORM:** [SQLAlchemy](https://www.sqlalchemy.org/)
*   **Database:** [SQLite](https://www.sqlite.org/)
*   **Password Hashing:** [bcrypt](https://pypi.org/project/bcrypt/)
*   **PDF Generation:** [ReportLab](https://www.reportlab.com/)
*   **Programming Language:** Python 3.x (developed with 3.10+)

## Prerequisites

*   Python 3.11 or higher.
*   `pip` (Python package installer).

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <repository_url>
    cd lottery-manager # Or your repository's directory name
    ```

2.  **Create a Virtual Environment (Recommended):**
    ```bash
    python -m venv venv
    # On Windows
    venv\Scripts\activate
    # On macOS/Linux
    source venv/bin/activate
    ```

3.  **Install Dependencies:**
    A `requirements.txt` file would typically be used. Based on the imports, the key dependencies are:
    ```
    flet
    sqlalchemy
    bcrypt
    reportlab
    ```
    You can install them using:
    ```bash
    pip install flet sqlalchemy bcrypt reportlab
    ```
    *(If a `requirements.txt` is provided in the future, use `pip install -r requirements.txt`)*

4.  **Directory Structure:**
    The application expects a `db_data` directory at the root level (where `main.py` resides or is run from) for the SQLite database and backups. This directory will be created automatically if it doesn't exist when the application first initializes the database.

## Running the Application

Once the setup is complete, run the application from the project's root directory:

```bash
python app/main.py
```

The application window will open, starting with the Login View.

## Initial Setup Flow (First Time Use)

Upon running the application for the first time, the database will be initialized.

1.  **Default Salesperson User:**
    A default "Salesperson" user is automatically created:
    *   Username: `sales`
    *   Password: `admin123`
        *(It is highly recommended to change this password after the initial setup via the Salesperson's user management interface if that feature were added, or by directly editing the database if necessary for security in a real deployment scenario. For now, the Admin user can edit this Salesperson user after being created.)*

2.  **Login as Salesperson:**
    Use the credentials above to log into the Salesperson Dashboard.

3.  **Create First Administrator:**
    *   Navigate to "User Account Management" on the Salesperson Dashboard.
    *   Click "Add New User".
    *   Create a user with the "Admin" role. This will be the primary administrator for the system.

4.  **Activate License:**
    *   On the Salesperson Dashboard, in the "License Management" section.
    *   Click "Activate License". The application license is now active.

5.  **Logout and Login as Admin:**
    *   Log out as the Salesperson.
    *   Log in using the credentials of the Admin user you just created.
    *   The Admin can now manage the application, create other Admin/Employee users, manage games, books, etc.

## Database

*   **Type:** SQLite
*   **Filename:** `lottery_manager.db`
*   **Location:** The database file is stored in the `db_data/` directory relative to where the application is run.
*   **Initialization:** Tables are created automatically on the first run if they don't exist.
*   **Backups:**
    *   The Admin role can trigger database backups.
    *   Backups are stored in `db_data/backups/YYYY/MM/YYYY-MM-DD_HH-MM-SS_lottery_manager.db`.

## Key Application Logic

### QR Code Scanning
*   The application supports QR code scanning for sales entry (Game-Book-Ticket format) and potentially for adding books (Game-Book format).
*   Constants define the expected lengths for game, book, and ticket parts of the scan.
*   A `ScanInputHandler` class manages debounced input from scanners to parse the data.

### Book Management
*   Books are instances of Games.
*   Each book has a `ticket_order` (`forward` or `reverse`) and `current_ticket_number`.
*   `REVERSE_TICKET_ORDER`: Tickets are sold from `total_tickets - 1` down to `0`. `current_ticket_number` is the highest available ticket. Sold out state is `-1`.
*   `FORWARD_TICKET_ORDER`: Tickets are sold from `0` up to `total_tickets - 1`. `current_ticket_number` is the next ticket to be sold. Sold out state is `total_tickets`.
*   Books must be activated before sales can be recorded against them.
*   Deactivating a book or marking it as fully sold sets its `finish_date`.

### Shift Submissions
*   Employees (or Admins acting as employees) submit shifts at the end of their sales period.
*   A `ShiftSubmission` record captures:
    *   User-reported cumulative totals from external terminals (online sales/payouts, instant payouts).
    *   Calculated delta values for these totals (current reported - sum of previous deltas for the same calendar day).
    *   Aggregated instant game sales (total tickets and value) processed during *this specific shift*. These are derived from `SalesEntry` records linked to the shift.
    *   A `net_drop_value` calculated as:
        `(delta_online_sales + total_instant_value_for_shift) - (delta_online_payouts + delta_instant_payouts_for_shift)`

## Future Enhancements (Ideas)

*   More detailed dashboard summaries (e.g., quick view of active stock value).
*   Password complexity rules and expiry for users.
*   Direct import/export of game/book data (e.g., CSV).
*   Enhanced logging for auditing purposes.
*   More granular permissions within roles.
*   Automated daily/weekly backup options.

## Contributing

Contributions are welcome! Please feel free to fork the repository, make changes, and submit a pull request. For major changes, please open an issue first to discuss what you would like to change.