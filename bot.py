# DISCLAIMER: This script is for educational purposes.
# By using this script, you acknowledge that you have read and agreed to the
# website's Terms of Service. The creator of this script is not responsible
# for any misuse, account restrictions, or IP bans that may result from its use.
# Automate responsibly.

import json
import os
import base64
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import tempfile
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, NoSuchElementException

def init_driver():
    """Initialize headless Chrome WebDriver (with GitHub Actions-safe options)."""
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=options)
    return driver

def load_credentials():
    """Read username/password from env, base64 env, or credentials.json."""
    username = os.environ.get("PIS_USERNAME")
    password = os.environ.get("PIS_PASSWORD")
    username_b64 = os.environ.get("PIS_USERNAME_B64")
    if username_b64:
        username = base64.b64decode(username_b64).decode("utf-8")
    if username and password:
        return username, password
    with open("credentials.json", "r", encoding="utf-8") as f:
        creds = json.load(f)
    return creds["username"], creds["password"]

def run_bot():
    """Log in to portal, navigate to applications page, and save HTML with retries."""
    import time
    MAX_RETRIES = 1
    WAIT_TIMEOUT = 5
    RETRY_DELAY = 2
    username, password = load_credentials()
    for attempt in range(MAX_RETRIES):
        driver = init_driver()
        try:
            print(f"Login attempt {attempt + 1} of {MAX_RETRIES}...")
            login_url = "https://myrequests.pis.gr/Account/Login.aspx"
            driver.get(login_url)
            wait = WebDriverWait(driver, WAIT_TIMEOUT)
            try:
                username_input = wait.until(EC.element_to_be_clickable((By.ID, "MainContent_LoginUser_UserName")))
                password_input = wait.until(EC.element_to_be_clickable((By.ID, "MainContent_LoginUser_Password")))
                login_button = wait.until(EC.element_to_be_clickable((By.ID, "MainContent_LoginUser_LoginButton")))
            except TimeoutException:
                print("Login form elements not found. Printing current page source for debugging:")
                print(driver.page_source)
                raise

            username_input.clear()
            username_input.send_keys(username)
            password_input.clear()
            password_input.send_keys(password)
            login_button.click()

            try:
                wait.until(EC.presence_of_element_located((By.LINK_TEXT, "Logout")))
            except TimeoutException:
                print("Login may have failed. Printing current page source for debugging:")
                print(driver.page_source)
                raise

            driver.get("https://myrequests.pis.gr/Applications.aspx")
            try:
                wait.until(EC.presence_of_element_located((By.TAG_NAME, "html")))
            except TimeoutException:
                print("Applications page did not load. Printing current page source for debugging:")
                print(driver.page_source)
                raise

            with open("application_view.html", "w", encoding="utf-8") as f:
                f.write(driver.page_source)
            print("✅ Login and scrape successful!")
            driver.quit()
            break
        except (TimeoutException, NoSuchElementException) as e:
            print(f"❌ Attempt {attempt + 1} failed. Server is likely busy or element not found.")
            driver.quit()
            if attempt < MAX_RETRIES - 1:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                print("All login attempts failed.")

if __name__ == "__main__":
    run_bot()
