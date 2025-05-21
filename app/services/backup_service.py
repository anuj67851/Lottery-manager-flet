import shutil
import datetime
import os
from typing import Tuple
from pathlib import Path # Import Path for type hinting if not already

from app.config import DB_FILENAME, DB_BASE_DIR

class BackupService:
    def create_database_backup(self) -> Tuple[bool, str]:
        """
        Creates a backup of the SQLite database file.

        The backup is stored in a structured directory: DB_BASE_DIR/backups/YYYY-MM-DD/
        The backup filename is timestamped: HH-MM-SS_original_db_filename.db

        Returns:
            Tuple[bool, str]: (True, path_to_backup_file) on success,
                              (False, error_message) on failure.
        """
        try:
            source_db_path: Path = DB_BASE_DIR.joinpath(DB_FILENAME)
            if not source_db_path.exists():
                return False, f"Source database file not found at '{source_db_path}'."

            now = datetime.datetime.now()
            date_str = now.strftime("%Y-%m-%d") # For daily folder
            time_str = now.strftime("%H-%M-%S") # For timestamped filename

            # Define the backup directory including the date
            backup_dir_for_today: Path = DB_BASE_DIR.joinpath("backups", date_str)

            # Create backup directory for the current date if it doesn't exist
            # This will create parent directories like "backups" as well if needed.
            os.makedirs(backup_dir_for_today, exist_ok=True)

            backup_filename = f"{time_str}_{DB_FILENAME}"
            backup_filepath: Path = backup_dir_for_today.joinpath(backup_filename)

            shutil.copy2(source_db_path, backup_filepath)

            return True, str(backup_filepath.resolve()) # Return resolved path for clarity

        except OSError as e:
            # More specific error for OS-level issues like permissions or disk full
            error_msg = f"OS error during backup (e.g., permissions, disk full): {e.strerror} (Path: '{e.filename}')."
            print(f"BackupService OS Error: {error_msg}") # Log for admin/dev
            return False, error_msg
        except Exception as e:
            error_msg = f"An unexpected error occurred during database backup: {type(e).__name__} - {e}."
            print(f"BackupService Unexpected Error: {error_msg}") # Log for admin/dev
            return False, error_msg