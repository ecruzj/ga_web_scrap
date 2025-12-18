from __future__ import annotations

import time
from datetime import date
from typing import List

from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, 
    NoSuchElementException, 
    StaleElementReferenceException,
    ElementClickInterceptedException
)
from selenium.webdriver.common.keys import Keys

from config import GA4_report_URL
from ..models.pageview_record import PageViewRecord

class GA4Scraper:
    def __init__(self, driver: WebDriver, timeout: int = 20) -> None:
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)

    def open_report(self) -> None:
        print("Opening Google Analytics 4 Report...")
        self.driver.get(GA4_report_URL)
        self._wait_for_spinner()

    def _wait_for_spinner(self):
        """
        Waits for the specific GA4 loader (<ga-loader>) to disappear.
        """
        try:
            time.sleep(1)
            self.wait.until(EC.invisibility_of_element_located((By.TAG_NAME, "ga-loader")))
            self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "ga-reporting-table")))
        except TimeoutException:
            print("Warning: GA4 Loading spinner timed out. Attempting to continue...")

    # ---------- Date Selection ----------

    def set_date_range(self, start: date, end: date) -> None:
        print(f"[GA4] Setting date range: {start} to {end}")
        
        try:
            date_btn = self.wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "ga-date-range-picker-v2 button.trigger-button"))
            )
            date_btn.click()
        except TimeoutException:
            raise RuntimeError("Could not find or click the GA4 Date Range trigger button.")

        try:
            calendar_container = self.wait.until(
                EC.visibility_of_element_located((By.TAG_NAME, "reach-date-range-calendar"))
            )
        except TimeoutException:
            raise RuntimeError("The Date Range Calendar did not open.")

        try:
            custom_option = calendar_container.find_element(By.CSS_SELECTOR, ".custom-option")
            custom_option.click()
            time.sleep(0.5)
        except NoSuchElementException:
            pass

        start_str = start.strftime("%b %d, %Y")
        end_str = end.strftime("%b %d, %Y")

        try:
            inputs = calendar_container.find_elements(By.CSS_SELECTOR, "reach-calendar-range-input input")
            if len(inputs) < 2:
                raise RuntimeError(f"Expected 2 date inputs, found {len(inputs)}")

            self._clear_and_type(inputs[0], start_str)
            self._clear_and_type(inputs[1], end_str)

            apply_btn = self.driver.find_element(By.XPATH, "//xap-card-footer//button[.//span[contains(text(), 'Apply')]]")
            
            if "mat-button-disabled" in apply_btn.get_attribute("class"):
                raise RuntimeError("Apply button is disabled. Check date format.")
            
            apply_btn.click()

        except Exception as e:
             raise RuntimeError(f"Failed to interact with date inputs/buttons: {e}")

        self.wait.until(EC.invisibility_of_element_located((By.TAG_NAME, "reach-date-range-calendar")))
        self._wait_for_spinner()
        time.sleep(2.0)

    def _clear_and_type(self, element: WebElement, text: str):
        element.click()
        element.send_keys(Keys.CONTROL + "a")
        element.send_keys(Keys.BACKSPACE)
        element.send_keys(text)
        element.send_keys(Keys.ENTER)
        time.sleep(0.2)

    # ---------- Rows Per Page Logic (NEW) ----------

    def _maximize_rows_per_page(self) -> None:
        """
        Selects '250' in the 'Rows per page' dropdown.
        """
        try:
            # 1. Find Dropdown
            dropdown = self.wait.until(
                EC.element_to_be_clickable((By.ID, "rows-per-page-select"))
            )
            
            # Check current value
            current_val_el = dropdown.find_element(By.CSS_SELECTOR, ".mat-mdc-select-value-text")
            if "250" in current_val_el.text:
                print("[GA4] Rows per page is already set to 250.")
                return

            print("[GA4] Switching to 250 rows per page...")
            dropdown.click()

            # 2. Wait for Options (mat-option inside cdk-overlay-pane)
            # We look for the option containing text '250'
            option_250 = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, "//mat-option//span[contains(text(), '250')]"))
            )
            option_250.click()

            # 3. Wait for table reload
            self._wait_for_spinner()
            time.sleep(1.5)

        except TimeoutException:
            print("Warning: Could not find or set 'Rows per page' to 250. Continuing with default.")
        except Exception as e:
            print(f"Warning: Error setting rows per page: {e}")

    # ---------- Scraping Logic ----------

    def scrape_data(self, the_date: date) -> List[PageViewRecord]:
        # 1. Optimize: Set rows to 250 BEFORE scraping
        self._maximize_rows_per_page()

        records = []
        max_pages = 100 
        current_page = 0

        try:
            table_container = self.wait.until(
                EC.presence_of_element_located((By.TAG_NAME, "ga-reporting-table"))
            )
        except TimeoutException:
            print("[GA4] No reporting table found on page.")
            return []

        while current_page < max_pages:
            current_page += 1
            print(f"[GA4] Scraping page {current_page}...")
            
            time.sleep(1.5) # Wait for table render
            
            rows = self.driver.find_elements(By.CSS_SELECTOR, "ga-reporting-table tbody tr.mat-mdc-row")
            
            if not rows:
                print("[GA4] No rows found.")
                break

            page_records_count = 0

            for row in rows:
                try:
                    # URL
                    url_cell = row.find_element(By.CSS_SELECTOR, "td[class*='unifiedPagePathScreen']")
                    url_text = url_cell.text.strip()

                    # Rank
                    try:
                        rank_cell = row.find_element(By.CSS_SELECTOR, "td[class*='__row_index__']")
                        rank = int(rank_cell.text.strip())
                    except:
                        rank = 0

                    # Views
                    views_cell = row.find_element(By.CSS_SELECTOR, "td[class*='screenPageViews']")
                    views_text_full = views_cell.text.strip()
                    views_clean = views_text_full.split('(')[0].strip().replace(",", "")
                    views = int(views_clean) if views_clean.isdigit() else 0

                    # Language Logic
                    lang_code = "EN" if "/en/" in url_text.lower() else "FR"

                    if url_text and url_text != "(not set)":
                        records.append(PageViewRecord(
                            date=the_date,
                            language=lang_code,
                            rank=rank,
                            url=url_text,
                            views=views,
                            source="Google Analytics"
                        ))
                        page_records_count += 1

                except StaleElementReferenceException:
                    continue
                except Exception:
                    continue
            
            print(f"   > Captured {page_records_count} records on this page.")

            # Pagination
            if not self._go_to_next_page():
                print("[GA4] Reached last page.")
                break
        
        return records

    def _go_to_next_page(self) -> bool:
        try:
            # Look for pagination controls inside the footer
            next_btn = self.driver.find_element(By.CSS_SELECTOR, "pagination button.page-increment")
            
            # Check if disabled
            classes = next_btn.get_attribute("class")
            if "button-disabled" in classes or next_btn.get_attribute("disabled"):
                return False

            next_btn.click()
            self._wait_for_spinner()
            return True

        except NoSuchElementException:
            return False