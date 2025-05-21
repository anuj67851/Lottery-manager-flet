from pathlib import Path
import os

# Database Configuration
DB_FILENAME = "lottery_manager.db"
DEFAULT_DB_BASE_DIR_NAME = "db_data"
DB_BASE_DIR_STR = os.environ.get("LOTTERY_DB_DIR", DEFAULT_DB_BASE_DIR_NAME)
DB_BASE_DIR = Path(DB_BASE_DIR_STR)

SQLALCHEMY_DATABASE_URL = f"sqlite:///{DB_BASE_DIR.joinpath(DB_FILENAME)}"

# License File Configuration
LICENSE_FILE_NAME = "license.key"
LICENSE_FILE_PATH = DB_BASE_DIR.joinpath(LICENSE_FILE_NAME)
LICENSE_ENCRYPTION_KEY = b'ZZ1Bqm7bRr94nvzJ7BfRUeVNePgcDYmB1WcYoYkBs3A='

VERSION_CONFIG = "version"
VERSION = "0.1"

# Application Settings
APP_TITLE = "Lottery Manager"
DEFAULT_THEME_MODE = "light" # "light" or "dark"