# src/ga_scraper/services/auth_service.py
import time
import os
from dotenv import load_dotenv
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

load_dotenv()

class GoogleAuthService:
    def __init__(self, driver: WebDriver):
        self.driver = driver
        self.wait = WebDriverWait(driver, 10)
        self.email = os.getenv("GOOGLE_EMAIL")
        self.password = os.getenv("GOOGLE_PASSWORD")

    def login(self):
        """
        Attempts to log in to Google. 
        WARNING: May be blocked by Google's 'This browser or app may not be secure'.
        Using a persistent User Data Dir is recommended instead.
        """
        # Check if we are already logged in (look for the account avatar or similar)
        try:
            # Simple check if we are redirected to login page or already in GA
            if "accounts.google.com" not in self.driver.current_url:
                print("Already logged in or not on login page.")
                return
        except:
            pass

        print("Attempting Google Login...")
        
        # Email
        email_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='email']")))
        email_input.clear()
        email_input.send_keys(self.email)
        self.driver.find_element(By.ID, "identifierNext").click()
        
        time.sleep(2)

        # Password
        pass_input = self.wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "input[type='password']")))
        pass_input.clear()
        pass_input.send_keys(self.password)
        self.driver.find_element(By.ID, "passwordNext").click()
        
        # Wait for redirection (handle 2FA manually if needed)
        print("Login credentials sent. Waiting for navigation...")
        time.sleep(5)