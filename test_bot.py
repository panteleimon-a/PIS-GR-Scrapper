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
    """Log in to portal, wait until xx Greek time, then repeatedly download the applications page for 1 minute, every 5 seconds, saving each with a timestamp."""
    start_time = time.time()
    username, password = load_credentials()

    login_url = "https://myrequests.pis.gr/Account/Login.aspx"
    applications_url = "https://myrequests.pis.gr/Applications.aspx"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
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
                print("Proceeding to applications page and starting 1-minute scrape window.")
                # Go to applications page
                page.goto(applications_url)
                page.wait_for_load_state("networkidle")
                # Wait until Greek time is 14:00
                now = get_greek_time()
                target_time = now.replace(hour=13, minute=59, second=59, microsecond=5)
                print(f"✅ Scheduled start reached. Already at /Applications page. Waiting until 14:00 Greek time before scraping...")
                loop_start = time.time()
                duration = 60  # seconds
                interval = 5   # seconds
                count = 0
                wait_until(target_time)
            # Start repeated download loop for 1 minute, every 5 seconds
            expected_files = ["application_view.pdf", "application_view.jpg", "application_view.html"]
            while True:
                now = time.time()
                if now - loop_start > duration:
                    break
                try:
                    greek_now = get_greek_time()
                    ts = greek_now.strftime("%Y%m%d_%H%M%S")
                    fname = f"application_view_{ts}.html"
                    print(f"Saving {fname}")
                    page_html = page.content()
                    with open(fname, "w", encoding="utf-8") as f:
                        f.write(page_html)
                    # --- Asset download enhancement ---
                    try:
                        from bs4 import BeautifulSoup
                        import os
                        soup = BeautifulSoup(page_html, "html.parser")
                        asset_dir = "application_assets"
                        os.makedirs(asset_dir, exist_ok=True)
                        # Find all asset links (PDFs, images)
                        asset_tags = []
                        asset_tags += soup.find_all("a", href=True)
                        asset_tags += soup.find_all("iframe", src=True)
                        asset_tags += soup.find_all("embed", src=True)
                        asset_tags += soup.find_all("img", src=True)
                        for tag in asset_tags:
                            url = tag.get("href") or tag.get("src")
                            if not url:
                                continue
                            if url.startswith("/"):
                                url = "https://myrequests.pis.gr" + url
                            if url.lower().endswith(".pdf") or url.lower().endswith(".jpg") or url.lower().endswith(".png"):
                                asset_name = os.path.basename(url.split("?")[0])
                                asset_path = os.path.join(asset_dir, asset_name)
                                try:
                                    asset_page = context.new_page()
                                    asset_page.goto(url)
                                    with open(asset_path, "wb") as af:
                                        af.write(asset_page.content().encode("utf-8"))
                                    asset_page.close()
                                    print(f"Downloaded asset: {asset_path}")
                                except Exception as asset_err:
                                    print(f"❌ Error downloading asset {url}: {asset_err}")
                    except Exception as soup_err:
                        print(f"❌ Error parsing HTML for assets: {soup_err}")
                    # --- End asset download enhancement ---
                    count += 1
                except Exception as e:
                    print(f"❌ Error during page save or reload: {e}")
                if now - loop_start + interval > duration:
                    break
                time.sleep(interval)
                try:
                    page.reload()
                    page.wait_for_load_state("networkidle")
                except Exception as e:
                    print(f"❌ Error during page reload: {e}")
            print(f"✅ Finished repeated downloads. Total pages saved: {count}")
            print(f"Expected asset files: {expected_files}")
            else:
                print("Login likely failed. Check credentials or form data.")
                with open("login_failed_response.html", "w", encoding="utf-8") as f:
                    f.write(content)
                print("Login response saved to login_failed_response.html for inspection.")
        finally:
            browser.close()

    end_time = time.time()
    elapsed = end_time - start_time
    print(f"⏱️ Total time taken: {elapsed:.2f} seconds.")

if __name__ == "__main__":
    print("Starting the web scraping process with Playwright...")
    run_scraper()
    print("Scraping process finished.")
