import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file if present
# URL of the Looker Studio report
LOOKER_STUDIO_URL = os.getenv("LOOKER_STUDIO_URL")

# Base directory (in case we want to save logs, Excel files, etc.)
BASE_DIR = Path(__file__).resolve().parents[1]

# Google Analytics 4 Report (Pages and Screens)
GA4_report_URL = os.getenv("GA4_report_URL")

# Default path where the Excel file will be generated
DEFAULT_OUTPUT = BASE_DIR / "ga_daily_pageviews.xlsx"

# Path to the Brave Browser executable
BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"