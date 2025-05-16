from pathlib import Path

# Database Configuration
DB_FILENAME = "lottery_manager.db"
DB_BASE_DIR = Path("db_data")  # Renamed for clarity
SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_BASE_DIR.joinpath(DB_FILENAME)}"

SALES_USERNAME = "anuj6785"
SALES_PASSWORD = "Hello@gent007"

# Application Settings
APP_TITLE = "Lottery Manager"
DEFAULT_THEME_MODE = "light" # "light" or "dark"