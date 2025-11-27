from pathlib import Path

# URL of the Looker Studio report
LOOKER_STUDIO_URL = (
    "https://lookerstudio.google.com/u/0/reporting/"
    "50106fec-7671-4d64-aff9-9aa4743834ae/page/yqZGF"
)

# Base directory (in case we want to save logs, Excel files, etc.)
BASE_DIR = Path(__file__).resolve().parents[1]

# Default path where the Excel file will be generated
DEFAULT_OUTPUT = BASE_DIR / "ga_daily_pageviews.xlsx"

# Path to the Brave Browser executable
BRAVE_PATH = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
