from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import SessionNotCreatedException, WebDriverException

def _get_brave_version(brave_path: str) -> str:
    """
    Returns Brave's Chromium version, e.g., '142.0.7444.60',
    without launching a visible Brave window.
    """
    # 1) Try Windows Registry (no UI)
    try:
        import winreg
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\BraveSoftware\Brave-Browser\BLBeacon"
        ) as key:
            v, _ = winreg.QueryValueEx(key, "version")
            if v:
                return v
    except Exception:
        pass

    # 2) Fallback: run brave --version but with NO WINDOW
    try:
        creationflags = 0x08000000  # CREATE_NO_WINDOW
        out = subprocess.check_output(
            [brave_path, "--version"],
            text=True,
            creationflags=creationflags
        ).strip()
        
        # Extract Chromium version using Regex
        m = re.search(r"Chromium:\s*([0-9.]+)", out)
        if m:
            return m.group(1)
        
        # Fallback to looking for any version-like number
        m2 = re.search(r"\b(\d+\.\d+\.\d+\.\d+)\b", out)
        return m2.group(1) if m2 else ""
    except Exception:
        return ""

def make_brave_driver(download_dir: Path, brave_path: str) -> webdriver.Chrome:
    """
    Creates a WebDriver instance for Brave Browser with a persistent profile
    to bypass Google Login blocks, automatically resolving the correct driver version.
    """
    options = Options()
    
    # 1. Point to Brave Binary
    options.binary_location = brave_path 
    
    # 2. CRITICAL: Anti-Detection Arguments
    # This hides the "Chrome is being controlled by automated test software" banner
    # and helps bypass Google's bot detection.
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    # 3. Persistence (User Data) settings
    # -------------------------------------------------------------------------
    windows_user = "CruzJosu" 
    user_data_path = fr"C:\Users\{windows_user}\AppData\Local\BraveSoftware\Brave-Browser\User Data"
    
    options.add_argument(f"user-data-dir={user_data_path}")
    options.add_argument("--profile-directory=Profile 3") 
    # -------------------------------------------------------------------------

    # 4. Basic Stability Arguments
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--remote-debugging-port=9222") # Helps prevent crashes with profiles

    # 5. Download preferences
    prefs = {
        "download.default_directory": str(download_dir),
        "download.prompt_for_download": False,
        "directory_upgrade": True,
        "safebrowsing.enabled": True,
        "credentials_enable_service": False, # Disable "Save password" popup
        "profile.password_manager_enabled": False
    }
    options.add_experimental_option("prefs", prefs)

    # --- DRIVER RESOLUTION LOGIC ---
    print(f"[Browser Resolver] Detecting Brave version at: {brave_path}")
    brave_ver = _get_brave_version(brave_path)
    major = brave_ver.split(".")[0] if brave_ver else ""
    
    driver_path = None

    try:
        if major.isdigit():
            print(f"[Browser Resolver] Detected version: {brave_ver} (Major: {major})")
            print(f"[Browser Resolver] Attempting to download ChromeDriver version {major}...")
            
            # This forces the download of the specific driver matching the local browser
            driver_path = ChromeDriverManager(driver_version=major).install()
        else:
            print("[Browser Resolver] Could not detect version, attempting to install 'latest'...")
            driver_path = ChromeDriverManager().install()

        service = Service(driver_path)
        driver = webdriver.Chrome(service=service, options=options)
        
        # Extra stealth step: Overwrite navigator.webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        print(f"Browser launched using profile: {user_data_path}")
        return driver

    except SessionNotCreatedException as e:
        msg = (
            "\n❌ SELENIUM SESSION ERROR ❌\n"
            f"Detected Brave Version: {brave_ver}\n"
            "The downloaded driver is incompatible.\n"
            "Solution: Verify if webdriver-manager supports this specific version (e.g. Beta/Nightly) or run 'pip install --upgrade webdriver-manager'.\n"
            f"Original Error: {e}"
        )
        raise RuntimeError(msg) from e
        
    except Exception as e:
        raise RuntimeError(
            f"Failed to initialize Brave driver.\n"
            f"1. CLOSE ALL BRAVE WINDOWS if using the Default profile.\n"
            f"2. Check 'brave_path' in config.py.\n"
            f"Error details: {e}"
        )