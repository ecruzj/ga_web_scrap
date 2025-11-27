from __future__ import annotations

from datetime import date
from pathlib import Path
from typing import Iterable

import pandas as pd

from ..models.pageview_record import PageViewRecord

def export_pageviews_to_excel(
    records: Iterable[PageViewRecord],
    output_path: Path,
    range_start: date | None = None,
    range_end: date | None = None,
) -> None:
    """
    Creates an Excel file with a single sheet containing both English and French data,
    differentiated by a 'language' column.
    """

    rows = []
    for r in records:
        row = {
            "date": r.date.isoformat(),
            "language": r.language.upper(), # Keep the language column
            "rank": r.rank,
            "url": r.url,
            "views": r.views,
        }

        if range_start is not None and range_end is not None:
            row["range_start"] = range_start.isoformat()
            row["range_end"] = range_end.isoformat()

        rows.append(row)

    if not rows:
        print("There are no records to export.")
        return

    df = pd.DataFrame(rows)

    # Reorder columns for better readability
    desired_order = ["date", "language", "rank", "url", "views"]
    
    # Add range columns to the order if they exist
    if "range_start" in df.columns:
        desired_order.extend(["range_start", "range_end"])
    
    # Ensure the dataframe follows the desired order
    # (Using intersection to avoid errors if a column is missing for some reason)
    final_cols = [c for c in desired_order if c in df.columns]
    df = df[final_cols]

    # DEBUG: See language distribution
    print("Exporting data distribution:", df["language"].value_counts().to_dict())

    # Write to a single sheet
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Data", index=False)

    print(f"Excel exported successfully with {len(df)} rows to: {output_path}")