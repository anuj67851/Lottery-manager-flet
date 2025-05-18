import datetime
from typing import Optional

def format_datetime_for_display(dt: Optional[datetime.datetime]) -> str:
    if dt is None:
        return "N/A"
    return dt.strftime("%Y-%m-%d %I:%M %p")