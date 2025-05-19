import shutil
import datetime
import os
from typing import Tuple

from app.config import DB_FILENAME, DB_BASE_DIR

class BackupService:
    def create_database_backup(self) -> Tuple[bool, str]:
        """
        Creates a backup of the SQLite database file.

        The backup is stored in a structured directory: db_data/backups/YYYY/MM/
        The backup filename is timestamped: YYYY-MM-DD_HH-MM-SS_original_db_filename.db

        Returns:
            Tuple[bool, str]: (True, path_to_backup_file) on success,
                              (False, error_message) on failure.
        """
        try:
            source_db_path = DB_BASE_DIR.joinpath(DB_FILENAME)
            if not source_db_path.exists():
                return False, f"Source database file not found at {source_db_path}"

            now = datetime.datetime.now()
            year_str = now.strftime("%Y")
            month_str = now.strftime("%m")
            timestamp_str = now.strftime("%Y-%m-%d_%H-%M-%S")

            backup_dir = DB_BASE_DIR.joinpath("backups", year_str, month_str)

            # Create backup directory if it doesn't exist
            os.makedirs(backup_dir, exist_ok=True)

            backup_filename = f"{timestamp_str}_{DB_FILENAME}"
            backup_filepath = backup_dir.joinpath(backup_filename)

            shutil.copy2(source_db_path, backup_filepath)

            return True, str(backup_filepath)

        except OSError as e:
            # More specific error for OS-level issues like permissions
            error_msg = f"OS error creating backup directory or copying file: {e}"
            print(f"BackupService Error: {error_msg}")
            return False, error_msg
        except Exception as e:
            error_msg = f"An unexpected error occurred during database backup: {e}"
            print(f"BackupService Error: {error_msg}")
            return False, error_msg