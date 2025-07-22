# -*- coding: utf-8 -*-
import os
import base64
import json
import time
from datetime import datetime, timedelta, timezone
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

def get_greek_time():
    # Greek time is UTC+3
    return datetime.now(timezone.utc) + timedelta(hours=3)

def wait_until(target_dt):
    """Wait until the target datetime (Greek time)."""
    while True:
        now = get_greek_time()
        if now >= target_dt:
            break
        wait_sec = (target_dt - now).total_seconds()
        print(f"Waiting {wait_sec:.1f} seconds until {target_dt.strftime('%Y-%m-%d %H:%M:%S')} Greek time...")
        time.sleep(min(wait_sec, 30))

def run_scraper():
    """Log in to portal, wait until 14:00 Greek time, then repeatedly download the applications page for 1 minute, every 5 seconds, saving each with a timestamp."""
    start_time = time.time()
    username, password = load_credentials()

    login_url = "https://myrequests.pis.gr/Account/Login.aspx"
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
            # Wait until 1 hour from now (current Greek time)
            now = get_greek_time()
            scheduled_start = now + timedelta(hours=1)
            if now < scheduled_start:
                print(f"Waiting {(scheduled_start - now).total_seconds():.1f} seconds until scheduled start at {scheduled_start.strftime('%Y-%m-%d %H:%M:%S')} Greek time...")
                wait_until(scheduled_start)
            print("✅ Scheduled start reached. Waiting 5 minutes before scraping...")
            wait_until(scheduled_start + timedelta(minutes=5))
            print("Proceeding to applications page and starting 1-minute scrape window.")
            # Go to applications page
            page.goto(applications_url)
            page.wait_for_load_state("networkidle")

            # Start repeated download loop for 1 minute, every 5 seconds
            loop_start = time.time()
            duration = 60  # seconds
            interval = 5   # seconds
            count = 0
            while True:
                now = time.time()
                if now - loop_start > duration:
                    break
                # Get Greek time for filename
                greek_now = get_greek_time()
                ts = greek_now.strftime("%Y%m%d_%H%M%S")
                fname = f"application_view_{ts}.html"
                print(f"Saving {fname}")
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(page.content())
                count += 1
                if now - loop_start + interval > duration:
                    break
                time.sleep(interval)
                # This is the codecell that makes sure the page is refreshed:
                page.reload()
                page.wait_for_load_state("networkidle")
            print(f"✅ Finished repeated downloads. Total pages saved: {count}")
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
