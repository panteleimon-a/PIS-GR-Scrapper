# -*- coding: utf-8 -*-
import os
import base64
import json
import time
from playwright.sync_api import sync_playwright

def load_credentials():
    """Read username/password from env, base64 env, or credentials.json."""
    username = os.environ.get("PIS_USERNAME")
    password = os.environ.get("PIS_PASSWORD")

    # If base64 encoded, decode it (good for complex chars in env vars)
    username_b64 = os.environ.get("PIS_USERNAME_B64")
    if username_b64:
        username = base64.b64decode(username_b64).decode("utf-8")

    if username and password:
        print("Credentials loaded from environment variables.")
        return username, password

    # Fallback to file if env vars not set
    try:
        with open("credentials.json", "r", encoding="utf-8") as f:
            creds = json.load(f)
        print("Credentials loaded from credentials.json file.")
        return creds["username"], creds["password"]
    except FileNotFoundError:
        raise Exception("Credentials not found. Please set PIS_USERNAME/PIS_PASSWORD env vars or create credentials.json.")

def run_scraper():
    """Log in to portal using Playwright, navigate to applications page, and save HTML. Also count time taken."""
    start_time = time.time()
    username, password = load_credentials()

    login_url = "https://myrequests.pis.gr/Account/Login.aspx"
    home_url = "https://myrequests.pis.gr/Default.aspx"
    applications_url = "https://myrequests.pis.gr/Applications.aspx"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print("Navigating to login page...")
        page.goto(login_url)

        # Fill in the login form
        print("Filling in login form...")
        page.fill('input[name="ctl00$MainContent$LoginUser$UserName"]', username)
        page.fill('input[name="ctl00$MainContent$LoginUser$Password"]', password)
        page.click('input[name="ctl00$MainContent$LoginUser$LoginButton"]')

        # Wait for navigation or user-specific element
        print("Waiting for login to complete...")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)  # Wait a bit for any redirects

        # After login, check for the presence of the user's name or logout link
        content = page.content()
        login_success = False
        try:
            welcome_span = page.query_selector("#HeadLoginView_HeadLoginName")
            if welcome_span:
                welcome_text = welcome_span.inner_text().strip()
                print(f"Found welcome name: {welcome_text}")
                login_success = True
        except Exception as e:
            print(f"Could not find welcome span: {e}")

        # Fallback: check for logout link
        if not login_success:
            try:
                logout_link = page.query_selector("#HeadLoginView_HeadLoginStatus")
                if logout_link:
                    print("Found logout link, login probably successful.")
                    login_success = True
            except Exception as e:
                print(f"Could not find logout link: {e}")

        if login_success:
            print("✅ Login successful! Navigating to applications page...")
            # Optionally, save the home page after login
            with open("home_page.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            # Go to applications page
            page.goto(applications_url)
            page.wait_for_load_state("networkidle")
            with open("application_view.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("✅ Applications page scraped successfully and saved to application_view.html")
        else:
            print("Login likely failed. Check credentials or form data.")
            with open("login_failed_response.html", "w", encoding="utf-8") as f:
                f.write(content)
            print("Login response saved to login_failed_response.html for inspection.")

        browser.close()

    end_time = time.time()
    elapsed = end_time - start_time
    print(f"⏱️ Total time taken: {elapsed:.2f} seconds.")

if __name__ == "__main__":
    print("Starting the web scraping process with Playwright...")
    run_scraper()
    print("Scraping process finished.")
