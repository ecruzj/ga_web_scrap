# Looker Studio Analytics Scraper

A robust Python automation tool designed to scrape Google Analytics pageview data from **Looker Studio** reports. It uses **Selenium** to navigate the UI, handle complex date pickers, scroll through data tables, and export bilingual (English/French) metrics into Excel.

## Key Features

*   **Advanced Date Navigation:** Automatically interacts with the Looker Studio date picker, handling Year/Month views and forcing "Fixed" mode for accurate selection.
*   **Bilingual Extraction:** Scrapes both "English Pages" and "French Pages" tables simultaneously.
*   **Smart Scrolling & Pagination:** Handles infinite scrolling within tables and navigates through multiple pagination pages to capture all rows.
*   **Two Operation Modes:**
    *   `per_day`: Extracts data day-by-day (useful for granular history).
    *   `range`: Extracts aggregated data for a specific date range.
*   **Excel Export:** Generates a clean `.xlsx` file containing combined data with a `Language` column.

## Prerequisites

*   **Python 3.10+**
*   **Brave Browser** (default configuration) or Google Chrome.
*   **Looker Studio Access:** You must have access to the target report URL.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/ecruzj/ga_web_scrap
    cd ga_daily_pageviews_scraper
    ```

2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
    *(Ensure `selenium`, `pandas`, and `openpyxl` are in your requirements)*.

3.  **Configuration:**
    Open `config.py` and update the following path to match your local installation of Brave Browser:
    ```python
    BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
    ```

##  Usage

The entry point is `src/ga_scraper/main.py`. You can adjust the dates and mode within the `__main__` block.

### 1. Per Day Mode
Extracts data for every single day between the start and end date. Creates one row per page per day.

```python
from datetime import date
from ga_scraper.main import run_scraper

# Scrape from Nov 1st to Nov 3rd, day by day
run_scraper(date(2025, 11, 1), date(2025, 11, 3), mode="per_day")

### 2. Range Mode
Extracts aggregated data for the entire selected period.

# Scrape the total views for the entire month of October
run_scraper(date(2025, 10, 1), date(2025, 10, 31), mode="range")