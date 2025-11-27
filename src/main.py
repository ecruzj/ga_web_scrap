# src/ga_scraper/main.py
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from selenium import webdriver

from config import BRAVE_PATH, DEFAULT_OUTPUT
from ga_scrapper.web_helper.browser import make_brave_driver
from ga_scrapper.services.date_range_service import iter_dates
from ga_scrapper.services.analytics_scraper import AnalyticsScraper
from ga_scrapper.services.excel_exporter import export_pageviews_to_excel


def run_scraper(
    start: date,
    end: date,
    base_output_dir: Path = DEFAULT_OUTPUT.parent,
    mode: str = "per_day",  # "per_day" or "range"
) -> None:
    """
    mode = "per_day": scrapes one record per day per URL (start..end).
    mode = "range": scrapes aggregated data for the full range [start, end].
    """
    
    # --- 1. Date Validation ---
    if start > end:
        print(f"Error: Start date ({start}) cannot be after end date ({end}).")
        return

    driver: webdriver.Chrome | None = None
    all_records = []

    # --- 2. Dynamic Filename Generation ---
    if mode == "per_day":
        filename = f"ga_data_daily_{start.isoformat()}_to_{end.isoformat()}.xlsx"
    else:
        filename = f"ga_data_range_{start.isoformat()}_to_{end.isoformat()}.xlsx"
    
    output_path = base_output_dir / filename

    try:
        # Setup Driver
        driver = make_brave_driver(
            download_dir=output_path.parent,
            brave_path=BRAVE_PATH,
        )
        scraper = AnalyticsScraper(driver)
        scraper.open_report()

        if mode == "per_day":
            # Loop through each day
            for d in iter_dates(start, end):
                print(f"--- Scraping date {d.isoformat()} ---")
                day_records = scraper.scrape_for_single_day(d)
                if not day_records:
                    print(f"No data found for {d.isoformat()}.")
                all_records.extend(day_records)

        else:
            # Single scrape for the whole range
            print(f"--- Scraping range {start.isoformat()} to {end.isoformat()} ---")
            scraper.set_date_range(start, end)
            
            # Note: For range mode, we typically assign the end_date 
            # or start_date to the record object, depending on preference.
            range_records = scraper.scrape_current_tables(end)
            all_records.extend(range_records)

        # --- 3. Empty Data Check & Export ---
        if not all_records:
            print("No records were captured during the scraping process.")
            print("Skipping Excel generation.")
            return

        range_start = start if mode == "range" else None
        range_end = end if mode == "range" else None

        print(f"Exporting {len(all_records)} records to {output_path}...")
        export_pageviews_to_excel(
            all_records, 
            output_path,
            range_start=range_start,
            range_end=range_end
        )
        print("Done.")

    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        if driver is not None:
            driver.quit()


if __name__ == "__main__":
    # Example Usage:
    
    # 1. Range Mode (e.g., Previous Years/Months)
    # run_scraper(date(2025, 11, 1), date(2025, 11, 27), mode="range")

    # 2. Daily Mode
    run_scraper(date(2025, 11, 1), date(2025, 11, 27), mode="per_day")