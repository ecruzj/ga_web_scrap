from dataclasses import dataclass
from datetime import date

@dataclass
class PageViewRecord:
    """
    Represents a row in the GA/Looker Studio table for a specific day.
    """
    date: date          # Day to which the views belong
    language: str       # 'EN' or 'FR'
    rank: int           # 1, 2, 3... according to the order in the table
    url: str            # URL displayed in the table (text of the <a>)
    views: int          # Number of views (no commas, integer)
    source: str         # New field: "Looker Studio" or "Google Analytics"