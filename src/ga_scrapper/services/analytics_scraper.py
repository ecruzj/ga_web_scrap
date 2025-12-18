# src/ga_scraper/services/analytics_scraper.py
from __future__ import annotations

import time
from datetime import date
from typing import List, Literal

from selenium.webdriver.remote.webdriver import WebDriver, WebElement
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import (
    StaleElementReferenceException,
    NoSuchElementException,
    TimeoutException,
    ElementClickInterceptedException
)
from selenium.webdriver.support import expected_conditions as EC

from ..models.pageview_record import PageViewRecord
from config import LOOKER_STUDIO_URL

LanguageCode = Literal["EN", "FR"]

# Mapping for Month parsing (Supports English and Spanish browsers)
MONTH_MAP = {
    "JAN": 1, "ENE": 1,
    "FEB": 2,
    "MAR": 3,
    "APR": 4, "ABR": 4,
    "MAY": 5,
    "JUN": 6,
    "JUL": 7,
    "AUG": 8, "AGO": 8,
    "SEP": 9, "SET": 9,
    "OCT": 10,
    "NOV": 11,
    "DEC": 12, "DIC": 12
}

class AnalyticsScraper:
    def __init__(self, driver: WebDriver, timeout: int = 20) -> None:
        self.driver = driver
        self.wait = WebDriverWait(driver, timeout)
        self._table_roots = {}

    # ---------- Basic Navigation ----------

    def open_report(self) -> None:
        print("Opening Looker Studio report...")
        self.driver.get(LOOKER_STUDIO_URL)
        self._wait_for_tables()

    def _wait_for_tables(self) -> bool:
        """
        Waits until at least the first rows of the tables are present.
        Returns True if found, False if timed out (empty report).
        """
        try:
            self.wait.until(
                EC.presence_of_all_elements_located(
                    (By.CSS_SELECTOR, "div.row.block-0.index-0")
                )
            )
            return True
        except TimeoutException:
            print("Warning: Tables did not load or contain no data.")
            return False

    # ---------- Date Picker Logic ----------

    def set_date_range(self, start: date, end: date) -> None:
        """
        Sets the date picker range to [start, end].
        Handles 'Auto' vs 'Fixed' mode and Year/Month navigation.
        """
        old_label = self._get_date_button_text()
        print(f"Opening date picker... (Current: {old_label})")

        # 1. Open date picker
        date_btn = self.wait.until(
            EC.element_to_be_clickable((By.CSS_SELECTOR, "button.canvas-date-input"))
        )
        date_btn.click()

        # 2. Wait for dialog
        dialog = self.wait.until(
            EC.visibility_of_element_located((By.CSS_SELECTOR, "ng2-date-picker-dialog"))
        )

        # --- Ensure 'Fixed' mode to enable calendars ---
        self._ensure_fixed_mode(dialog)

        # 3. Identify calendars
        calendars = dialog.find_elements(By.CSS_SELECTOR, "mat-calendar")
        if len(calendars) < 2:
            raise RuntimeError(f"Expected 2 calendars, found: {len(calendars)}")

        start_cal = calendars[0]
        end_cal = calendars[1]

        # 4. Select dates
        print(f"Selecting start date: {start}")
        self._click_day(start_cal, start)
        time.sleep(0.8)

        print(f"Selecting end date: {end}")
        self._click_day(end_cal, end)

        # 5. Apply
        apply_btn = dialog.find_element(By.CSS_SELECTOR, "button.apply-button")
        apply_btn.click()

        # 6. Wait for dialog to close
        self.wait.until(
            EC.invisibility_of_element_located((By.CSS_SELECTOR, "ng2-date-picker-dialog"))
        )

        # 7. Wait for button text change (confirmation)
        try:
            self.wait.until(lambda d: self._get_date_button_text() != old_label)
        except TimeoutException:
            print("Date button text didn't change (range might be identical). Continuing...")

        # 8. Wait for tables to refresh
        self._wait_for_tables()
        time.sleep(4.0) # Grace period for data rendering

    def _ensure_fixed_mode(self, dialog_root: WebElement) -> None:
        """
        Ensures the date picker is in 'Fixed' mode.
        """
        try:
            options_btn = dialog_root.find_element(By.CSS_SELECTOR, "button.date-range-options")
            current_text = options_btn.text.strip().lower()

            if "fixed" in current_text:
                return

            print(f"Switching date mode from '{options_btn.text.strip()}' to 'Fixed'...")
            options_btn.click()

            # Find 'Fixed' item in the dropdown menu using XPath
            fixed_item_xpath = "//button[@role='menuitem']//span[contains(text(), 'Fixed')]/ancestor::button"
            fixed_item = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, fixed_item_xpath))
            )
            fixed_item.click()

            # Wait for confirmation
            self.wait.until(lambda d: "fixed" in options_btn.text.lower())
            time.sleep(1.0)

        except (NoSuchElementException, TimeoutException) as e:
            print(f"Warning: Could not switch to 'Fixed' mode. Error: {e}")

    def _click_day(self, calendar_root: WebElement, target: date) -> None:
        """
        Navigates to the correct Month/Year and clicks the specific day.
        """
        # 1. Navigate to correct view
        self._shift_calendar_to_month(calendar_root, target)

        # 2. Click the day (robust XPath for any tag inside the cell)
        day_str = str(target.day)
        xpath = (
            f".//td[not(contains(@class, 'mat-calendar-body-disabled'))]"
            f"//*[contains(@class, 'mat-calendar-body-cell-content') and normalize-space(text())='{day_str}']"
        )

        try:
            day_content = calendar_root.find_element(By.XPATH, xpath)
            # Try clicking the parent button if it's a span, otherwise click element itself
            try:
                clickable_el = day_content.find_element(By.XPATH, "./ancestor::button[1]")
            except NoSuchElementException:
                clickable_el = day_content

            self.driver.execute_script("arguments[0].click();", clickable_el)
        except NoSuchElementException:
            raise RuntimeError(f"Could not find day {day_str} in calendar for {target}.")

    def _shift_calendar_to_month(self, calendar_root: WebElement, target: date) -> None:
        """
        Moves the calendar to the target Month and Year.
        Handles Year-View and Month-View transitions.
        """
        max_steps = 48  # Safety limit (approx 4 years)

        for _ in range(max_steps):
            try:
                header = calendar_root.find_element(By.CSS_SELECTOR, "div.mat-calendar-controls")
                period_btn = header.find_element(By.CSS_SELECTOR, "button.mat-calendar-period-button")
                current_label = period_btn.text.strip()
            except Exception:
                time.sleep(0.5)
                continue

            # --- Case 1: Year Range View (e.g., "2016 – 2039") ---
            if "–" in current_label or "-" in current_label:
                # print(f"Calendar in range view ({current_label}). Selecting year {target.year}...")
                year_xpath = (
                    f".//td[@role='gridcell']//*[contains(@class, 'mat-calendar-body-cell-content') "
                    f"and normalize-space(text())='{target.year}']"
                )
                try:
                    year_content = calendar_root.find_element(By.XPATH, year_xpath)
                    year_btn = year_content.find_element(By.XPATH, "./ancestor::button[1]")
                    year_btn.click()
                    time.sleep(1.0)
                    continue
                except NoSuchElementException:
                    raise RuntimeError(f"Year {target.year} not visible in view {current_label}")

            parts = current_label.split()

            # --- Case 2: Month Selection View (e.g., "2025") ---
            if len(parts) == 1 and parts[0].isdigit():
                target_month_idx = target.month
                # Find key by value in MONTH_MAP
                month_key = [k for k, v in MONTH_MAP.items() if v == target_month_idx][0]

                month_xpath = (
                    f".//td[@role='gridcell']//*[contains(@class, 'mat-calendar-body-cell-content') "
                    f"and contains(translate(text(), 'abcdefghijklmnopqrstuvwxyz', 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'), '{month_key}')]"
                )
                try:
                    month_content = calendar_root.find_element(By.XPATH, month_xpath)
                    month_btn = month_content.find_element(By.XPATH, "./ancestor::button[1]")
                    month_btn.click()
                    time.sleep(1.0)
                    continue
                except NoSuchElementException:
                    pass

            # --- Case 3: Day View (e.g., "NOV 2025") ---
            if len(parts) < 2:
                # Unknown state, click header to zoom out
                period_btn.click()
                time.sleep(1.0)
                continue

            month_str = parts[0].upper()[:3]
            try:
                year_val = int(parts[-1])
            except ValueError:
                period_btn.click()
                continue

            if month_str not in MONTH_MAP:
                period_btn.click()
                continue

            month_val = MONTH_MAP[month_str]

            # Target reached?
            if year_val == target.year and month_val == target.month:
                return

            # Navigation Logic
            diff = (target.year - year_val) * 12 + (target.month - month_val)
            btn_class = "mat-calendar-previous-button" if diff < 0 else "mat-calendar-next-button"

            try:
                nav_btn = header.find_element(By.CSS_SELECTOR, f"button.{btn_class}")
            except NoSuchElementException:
                period_btn.click()
                continue

            # If button disabled, go up to year view
            if "disabled" in nav_btn.get_attribute("class") or nav_btn.get_attribute("disabled"):
                print(f"Navigation blocked at {current_label}. Switching to Year view...")
                period_btn.click()
                time.sleep(1.0)
                continue

            nav_btn.click()

            # Wait for update
            try:
                self.wait.until(
                    lambda d: calendar_root.find_element(By.CSS_SELECTOR, "button.mat-calendar-period-button").text.strip() != current_label
                )
            except TimeoutException:
                pass # Loop will re-check

            time.sleep(0.2)

        raise RuntimeError(f"Could not reach month {target} after {max_steps} attempts.")

    def _get_date_button_text(self) -> str:
        btn = self.driver.find_element(By.CSS_SELECTOR, "button.canvas-date-input")
        return btn.text.strip()

    # ---------- Table Scraping Logic ----------

    def _get_table_containers(self):
        """
        Identifies EN and FR tables dynamically based on headers.
        """
        tables = self.driver.find_elements(By.CSS_SELECTOR, "div.table")
        container_en = None
        container_fr = None
        self._table_roots = {}

        for t in tables:
            try:
                # Looker Studio headers
                headers = t.find_elements(By.CSS_SELECTOR, "div.headerRow .colName")
                full_text = " ".join([h.text for h in headers]).lower()
            except Exception:
                continue

            if "en pages" in full_text or "english" in full_text:
                self._table_roots["EN"] = t
                container_en = t.find_element(By.CSS_SELECTOR, "div.tableBody div.centerColsContainer")
            elif "fr pages" in full_text or "french" in full_text:
                self._table_roots["FR"] = t
                container_fr = t.find_element(By.CSS_SELECTOR, "div.tableBody div.centerColsContainer")

        # Fallback by position if headers are missing/different
        if not container_en or not container_fr:
            if len(tables) >= 2:
                self._table_roots["EN"] = tables[0]
                container_en = tables[0].find_element(By.CSS_SELECTOR, "div.tableBody div.centerColsContainer")
                self._table_roots["FR"] = tables[1]
                container_fr = tables[1].find_element(By.CSS_SELECTOR, "div.tableBody div.centerColsContainer")
            else:
                raise RuntimeError("Could not identify EN/FR tables.")

        return container_en, container_fr

    def _get_table_root(self, lang: LanguageCode):
        return self._table_roots[lang]

    def _scrape_table_for_language(
        self, lang: LanguageCode, the_date: date
    ) -> List[PageViewRecord]:
        """
        Scrapes the table for a specific language using scrolling and pagination.
        Optimized for speed compared to previous versions.
        """
        # Initialize containers
        container_en, container_fr = self._get_table_containers()
        records_map: dict[tuple[int, str], PageViewRecord] = {}

        max_rank_seen = 0
        max_pages = 10  # Safety limit

        for page_idx in range(max_pages):
            # Refresh containers in case DOM changed
            container_en, container_fr = self._get_table_containers()
            container = container_en if lang == "EN" else container_fr
            table_root = self._get_table_root(lang)

            # Reset scroll to top for new page
            try:
                self.driver.execute_script("arguments[0].scrollTop = 0;", container)
            except StaleElementReferenceException:
                pass
            time.sleep(0.3)

            # ---- Internal Scroll Loop ----
            max_scrolls = 40
            consecutive_no_new_records = 0

            for i in range(max_scrolls):
                rows = container.find_elements(By.CSS_SELECTOR, "div.row")
                if not rows:
                    break

                before_count = len(records_map)

                for row in rows:
                    try:
                        cells = row.find_elements(By.CSS_SELECTOR, "div.cell")
                        if len(cells) < 3:
                            continue

                        # Rank
                        rank_text = cells[0].text.strip().replace(".", "").strip()
                        if not rank_text.isdigit():
                            continue # Skip 'Grand total' or non-numeric rows
                        rank = int(rank_text)

                        # URL
                        try:
                            link_el = cells[1].find_element(By.TAG_NAME, "a")
                            url_text = link_el.text.strip()
                        except NoSuchElementException:
                            url_text = cells[1].text.strip()

                        # Views
                        views_text = cells[2].text.strip().replace(",", "")
                        try:
                            views = int(views_text)
                        except ValueError:
                            views = 0

                        key = (rank, url_text)
                        # Upsert record
                        records_map[key] = PageViewRecord(
                            date=the_date,
                            language=lang,
                            rank=rank,
                            url=url_text,
                            views=views,
                            source="Looker Studio"
                        )

                        if rank > max_rank_seen:
                            max_rank_seen = rank

                    except StaleElementReferenceException:
                        continue

                after_count = len(records_map)
                
                # Logging progress
                print(f"[{lang}] Page {page_idx + 1} Scroll {i + 1}: Total Unique Records: {after_count}, Max Rank: {max_rank_seen}")

                # Stop scrolling if no new records found for 2 consecutive scrolls
                if after_count == before_count:
                    consecutive_no_new_records += 1
                else:
                    consecutive_no_new_records = 0
                
                if consecutive_no_new_records >= 2:
                    break

                # Scroll Down
                try:
                    self.driver.execute_script(
                        "arguments[0].scrollTop = arguments[0].scrollTop + arguments[0].clientHeight;",
                        container,
                    )
                except StaleElementReferenceException:
                    pass
                
                # Optimized sleep time
                time.sleep(0.3)

            # ---- Pagination Logic ----
            try:
                pager = table_root.find_element(By.CSS_SELECTOR, "div.pageControl")
                next_btn = pager.find_element(By.CSS_SELECTOR, "div.pageForward")
            except NoSuchElementException:
                break # No pagination controls

            # Check if next button is disabled
            classes = (next_btn.get_attribute("class") or "").split()
            if "disabled" in classes:
                break # Last page reached

            # Click Next Page
            next_btn.click()
            print(f"[{lang}] Moving to page {page_idx + 2}...")
            time.sleep(0.8) # Wait for page load #3.0 s

        records = list(records_map.values())
        print(f"[{lang}] Capture complete. Total unique records: {len(records)}")
        return records

    # ---------- Public Methods ----------

    def scrape_current_tables(self, the_date: date) -> List[PageViewRecord]:
        """
        Scrapes current EN and FR tables without changing dates.
        """
        if not self._wait_for_tables():
            return []
            
        en_records = self._scrape_table_for_language("EN", the_date)
        fr_records = self._scrape_table_for_language("FR", the_date)
        return en_records + fr_records

    def scrape_for_single_day(self, the_date: date) -> List[PageViewRecord]:
        """
        Sets date to [the_date, the_date] and scrapes.
        """
        self.set_date_range(the_date, the_date)
        return self.scrape_current_tables(the_date)