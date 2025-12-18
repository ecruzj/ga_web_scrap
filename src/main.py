# src/ga_scraper/main.py
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

from selenium import webdriver

from config import BRAVE_PATH, DEFAULT_OUTPUT
from ga_scrapper.web_helper.browser import make_brave_driver
from ga_scrapper.services.date_range_service import iter_dates
from ga_scrapper.services.excel_exporter import export_pageviews_to_excel
from ga_scrapper.services.auth_service import GoogleAuthService

# Import Scrapers
from ga_scrapper.services.analytics_scraper import AnalyticsScraper # Looker Studio
from ga_scrapper.services.ga4_scraper import GA4Scraper # New GA4 Source

def run_scraper(
    start: date,
    end: date,
    base_output_dir: Path = DEFAULT_OUTPUT.parent,
    mode: str = "per_day",  # "per_day" or "range"
    sources: list[str] = ["looker", "ga4"] # Control which sources to scrape
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
        filename = f"ga_multisource_data_daily_{start.isoformat()}_to_{end.isoformat()}.xlsx"
    else:
        filename = f"ga_multisource_data_range_{start.isoformat()}_to_{end.isoformat()}.xlsx"
    
    output_path = base_output_dir / filename

    try:
        # Setup Driver
        driver = make_brave_driver(
            download_dir=output_path.parent,
            brave_path=BRAVE_PATH,
        )
        
        # --- 1. Authenticate (Needed for GA4) ---
        if "ga4" in sources:
            auth = GoogleAuthService(driver)
            auth.login()

        # --- 2. Scrape Looker Studio ---
        if "looker" in sources:
            print(">>> Starting Looker Studio Scraping...")
            looker_scraper = AnalyticsScraper(driver)
            looker_scraper.open_report()
            
            if mode == "per_day":
                for d in iter_dates(start, end):
                    print(f"[Looker] Processing date {d.isoformat()}...")
                    recs = looker_scraper.scrape_for_single_day(d)
                    for r in recs: r.source = "Looker Studio" # Ensure source is set
                    all_records.extend(recs)
            else:
                print(f"[Looker] Processing range {start} to {end}...")
                looker_scraper.set_date_range(start, end)
                recs = looker_scraper.scrape_current_tables(end)
                for r in recs: r.source = "Looker Studio"
                all_records.extend(recs)

        # --- 3. Scrape Google Analytics 4 ---
        if "ga4" in sources:
            print(">>> Starting Google Analytics 4 Scraping...")
            ga4_scraper = GA4Scraper(driver)
            ga4_scraper.open_report()

            if mode == "per_day":
                 for d in iter_dates(start, end):
                    print(f"[GA4] Processing date {d.isoformat()}...")
                    ga4_scraper.set_date_range(d, d)
                    recs = ga4_scraper.scrape_data(d)
                    all_records.extend(recs)
            else:
                print(f"[GA4] Processing range {start} to {end}...")
                ga4_scraper.set_date_range(start, end)
                # For range, we treat the 'date' column as the end date for reference
                recs = ga4_scraper.scrape_data(end)
                all_records.extend(recs)

        # --- 4. Export ---
        if not all_records:
            print("No records captured.")
            return

        print(f"Exporting {len(all_records)} records to {output_path}...")
        
        range_start = start if mode == "range" else None
        range_end = end if mode == "range" else None
        
        export_pageviews_to_excel(all_records, output_path, range_start, range_end)
        print("Done.")

    except Exception as e:
        print(f"Critical Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()


if __name__ == "__main__":
    # Example Usage:
    
    # 1. Range Mode (e.g., Previous Years/Months)
    run_scraper(date(2025, 12, 1), date(2025, 12, 18), mode="range", sources=["looker", "ga4"])

    # 2. Daily Mode
    # run_scraper(date(2025, 12, 1), date(2025, 12, 5), mode="per_day", sources=["looker", "ga4"])