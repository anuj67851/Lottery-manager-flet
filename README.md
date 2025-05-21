# Lottery Manager Application ✨

**Version:** 0.1

---

## Table of Contents

1.  [Overview](#overview-️)
2.  [Key Features](#key-features-)
    *   [User Authentication & Roles](#secure-user-authentication--role-management-)
    *   [License Control](#license-control-)
    *   [Inventory Management](#comprehensive-inventory-management-)
    *   [Sales & Shift Operations](#efficient-sales--shift-operations-)
    *   [Reporting](#insightful-reporting-admin-access-)
    *   [Data Management & Integrity](#data-management--integrity-)
    *   [System Operations](#system-operations-)
3.  [Technical Specifications](#technical-specifications-)
4.  [Installation and Running (Windows)](#installation-and-running-windows-application-)
    *   [Prerequisites](#prerequisites)
    *   [Installation Steps](#installation)
    *   [Running the Application](#running-the-application)
    *   [First-Run Setup](#first-run-setup)
    *   [Data Directory (`db_data`)](#data-directory-db_data)
5.  [Using the Application](#using-the-application-)
6.  [Included Assets](#included-assets-)
7.  [Support](#support-)

---

## 1. Overview ℹ️

The **Lottery Manager** is a user-friendly desktop application designed for small businesses to efficiently manage lottery ticket inventory, track sales, handle shift submissions, and generate insightful reports. Built with Python and the modern Flet UI framework, it utilizes an SQLite database for reliable local data storage and ReportLab for PDF report generation.

This application is intended for single-user operation at any given time on a Windows PC.

## 2. Key Features 🌟

### Secure User Authentication & Role Management 🔑

*   **First-Run Setup:** Guides the owner to create a primary **Salesperson/Owner** account with full administrative privileges upon initial launch.
*   **Role-Based Access Control:** Clear separation of duties based on user roles.

    | Role                  | Key Responsibilities & Permissions                                                                                                                                 |
    | :-------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
    | **Salesperson (Owner)**| Manages application license; Creates/manages Admin and Employee accounts. Can view all user activities (implicitly).                                                |
    | **Admin**              | Manages game and book inventory; Performs special sales operations (e.g., full book sale); Generates all financial/inventory reports; Manages Admin/Employee accounts.|
    | **Employee**           | Primarily handles daily sales entry and end-of-shift submissions.                                                                                                   |                                                                                                  |  
* User accounts can be **activated** or **deactivated** (except Salesperson via general UI).
*   Robust input validation for user credentials and details to ensure data quality.

### License Control  aktiviert

*   Application license status is securely stored in an **encrypted `license.key` file**, independent of the main operational database, enhancing tamper resistance.
*   The Salesperson/Owner can easily activate or deactivate the application license through their dedicated dashboard.
*   Admin and Employee functionalities require an active license.

### Comprehensive Inventory Management 📚

*   **Game Management:**
    *   Create, view, edit, and manage the lifecycle (expire/reactivate) of different lottery game types.
    *   Define game price (stored in cents, displayed in dollars), total tickets per book, default ticket counting order (forward/reverse), and unique game numbers.
*   **Book Management:**
    *   Add new physical lottery ticket books, linking them to specific games.
    *   View and edit book details including book number, current ticket number.
    *   Ticket order can be changed *only if no sales are recorded* for the book.
    *   Activate or deactivate books for sales processing.
    *   Securely delete books (if inactive and have no sales history).
    *   Supports batch addition of books for efficiency.

### Efficient Sales & Shift Operations 💸

*   **Sales Entry:**
    *   Streamlined interface for recording instant game ticket sales.
    *   Supports **QR code scanning** (Game No + Book No + Ticket No) for rapid and accurate input.
    *   The system intelligently handles new book entries: if a scanned book (for an existing game) is not yet in inventory, it's automatically created and activated.
*   **Shift Submissions:**
    *   Employees and Admins can submit detailed end-of-shift reports.
    *   Inputs include:
        *   Manually reported cumulative totals for online sales & payouts (from external terminals).
        *   Manually reported cumulative totals for instant game payouts.
        *   Actual cash counted in the lottery drawer.
    *   The system automatically calculates net deltas for these transactions for the current shift based on previous submissions for the same calendar day.
    *   Tracks total instant tickets sold and their value for the shift.
    *   Provides a calculated expected drawer value and clearly highlights any drawer difference (shortfall/overage).

### Insightful Reporting (Admin Access) 📊

All reports are exportable to PDF format.

| Report Name             | Description                                                                                                                                      | Filters Available                               |
| :---------------------- | :----------------------------------------------------------------------------------------------------------------------------------------------- | :---------------------------------------------- |
| **Sales & Shifts Report** | Comprehensive details of individual instant game sales and summarized shift submissions. Includes overall financial summaries for the period.    | Date Range, User                                |
| **Open Books Report**   | Lists all currently active lottery books, showing remaining tickets, ticket price, and total remaining monetary value for each.                  | Game                                            |
| **Game Expiry Report**  | Overview of all games, their status (active/expired), creation dates, and expiration dates.                                                    | Status (Active/Expired), Expiry Date Range    |
| **Stock Levels Report** | Summarizes book counts (total, active, finished, pending) and the total monetary value of active stock for each game.                            | Game                                            |

### Data Management & Integrity 🛡️

*   **Database Backup:** Admins can initiate a manual backup of the entire application database.
    *   Backups are timestamped and organized into daily folders: `[data_directory]/backups/YYYY-MM-DD/HH-MM-SS_lottery_manager.db`.
*   **Input Validation:** Extensive validation on user inputs across all modules to ensure data integrity and prevent errors.
*   **Error Handling:** Graceful handling of common operational errors with user-friendly feedback messages.

### System Operations ⚙️

*   **Logging:** Detailed application activity, warnings, and errors are logged to a daily rotating file: `[data_directory]/lottery_manager.log`. This aids in troubleshooting and support. Unhandled exceptions are also captured.
*   **Configurable Data Directory:** The primary location for the database, license file, logs, and backups can be specified via the `LOTTERY_DB_DIR` environment variable, offering deployment flexibility.

## 3. Technical Specifications 💻

*   **Core Language:** Python 3.x
*   **Graphical User Interface:** Flet Framework
*   **Database Engine:** SQLite (via SQLAlchemy ORM)
*   **Password Hashing:** bcrypt
*   **File Encryption:** `cryptography` library (Fernet symmetric encryption for `license.key`)
*   **PDF Generation:** ReportLab Toolkit

## 4. Installation and Running (Windows Application) 🚀

This application is packaged for Windows using PyInstaller (via `flet pack`).

### Prerequisites

*   Windows Operating System (Windows 7 / 8 / 10 / 11).
*   No separate Python installation is required for the packaged application.

### Installation

1.  Locate the distribution folder created by the `flet pack ... --onedir` command (typically `dist/Lottery Manager/`). This folder contains `Lottery Manager.exe` and all necessary supporting files.
2.  Copy this entire **"Lottery Manager"** folder to a desired location on your computer (e.g., `C:\Program Files\Lottery Manager` or onto the Desktop).

### Running the Application

1.  Navigate into the "Lottery Manager" folder where you copied the files.
2.  Double-click on **`Lottery Manager.exe`** to start the application.

### First-Run Setup

*   When you run the application for the very first time (or if the data directory has been cleared), a setup screen will appear.
*   You will be prompted to create the primary **Salesperson/Owner** account. This account is crucial for managing the application's license and other user accounts.
*   Enter a secure username and password as instructed on-screen.

### Data Directory (`db_data`)

*   Upon first run, the application will automatically create a subdirectory named `db_data` **inside the same folder where `Lottery Manager.exe` is located**.
*   This `db_data` folder is vital and will store:
    *   `lottery_manager.db`: The main application database.
    *   `license.key`: The encrypted file storing the license activation status.
    *   `lottery_manager.log`: The primary application log file (this file rotates daily, keeping recent history).
    *   `backups/`: A subdirectory where database backups (initiated by an Admin) will be saved.
*   **Important:** Do not manually delete or modify files within the `db_data` directory unless you understand the consequences (e.g., deleting `lottery_manager.db` will reset all application data and require re-running the first-run setup).
*   **Custom Data Directory (Advanced):**
    If you need to store the `db_data` folder in a location different from where `Lottery Manager.exe` resides, you can set the `LOTTERY_DB_DIR` environment variable on your system *before* launching the application.
    *   Example (Command Prompt): `set LOTTERY_DB_DIR="D:\MyAppStorage\LotteryData"`
    *   Example (PowerShell): `$env:LOTTERY_DB_DIR="D:\MyAppStorage\LotteryData"`
        Then run `Lottery Manager.exe`. The data folder and its contents will be created/used in the specified custom path.

## 5. Using the Application 🖱️

1.  **Login:** After the first-run setup (if applicable), the login screen will appear. Enter your credentials.
2.  **Dashboard Navigation:** Based on your user role (Salesperson, Admin, or Employee), you will be directed to the appropriate dashboard with access to relevant features.
3.  **License Activation:** For full functionality (Admin/Employee dashboards), the license must be activated by the Salesperson. The Salesperson dashboard is always accessible for license management.
4.  **Database Backups:** Admins should regularly use the "Backup Database" feature. **It is highly recommended to copy these backup files to an external storage device (like a USB drive) or a secure cloud location for disaster recovery.**
5.  **Troubleshooting:** If you encounter any issues:
    *   Note down any error messages displayed by the application.
    *   The primary log file (`lottery_manager.log` located inside the `db_data` folder) contains detailed technical information. This file can be very helpful for support or developers to diagnose problems.

## 6. Included Assets 🖼️

The `assets` folder (which is bundled with the application by PyInstaller due to `--add-data "assets:assets"`) contains:
*   `app_icon.ico`: The application icon used for the executable and window.
    *(You can list other assets here if you add more, e.g., images, fonts)*

## 7. Support 📧

For support, questions, or feedback, please contact: **anujpatel6785@gmail.com**

---
**Product Name:** Lottery Manager
**File Description:** Lottery Ticket Management Application