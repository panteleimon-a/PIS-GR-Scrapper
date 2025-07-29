# -*- coding: utf-8 -*-
import os
import base64
import json
import time
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError, Error as PlaywrightError
from bs4 import BeautifulSoup

# --- Configuration ---
# Define the exact date and time of the event in Greek time (UTC+3)
# IMPORTANT: Adjust these values to the actual event date and time
EVENT_YEAR = 2025
EVENT_MONTH = 7  # July (based on your cron schedule)
EVENT_DAY = 29   # 29th
EVENT_HOUR = 14  # 14:00 EEST
EVENT_MINUTE = 0
EVENT_SECOND = 0
EVENT_MICROSECOND = 0 # Aim for the very start of the second

LOGIN_URL = "https://myrequests.pis.gr/Account/Login.aspx"
APPLICATIONS_URL = "https://myrequests.pis.gr/Applications.aspx"

MIN_SUCCESS_SAVES = 5  # Goal: save the applications page at least this many times
MAX_SCRAPE_LOOP_ATTEMPTS = 200 # Safety net: stop after this many attempts if MIN_SUCCESS_SAVES not met
SCRAPE_WINDOW_DURATION_SECONDS = 60 # How long to keep trying after target time
SCRAPE_INTERVAL_SECONDS = 5 # How often to try refreshing the page

PAGE_OPERATION_TIMEOUT_MS = 15000 # 15 seconds for page operations (goto, reload, wait_for_load_state)

# --- Helper Functions ---

def load_credentials():
    """Read username/password from env, base64 env, or credentials.json."""
    username = os.environ.get("PIS_USERNAME")
    password = os.environ.get("PIS_PASSWORD")

    username_b64 = os.environ.get("PIS_USERNAME_B64")
    if username_b64:
        username = base64.b64decode(username_b64).decode("utf-8")

    if username and password:
        print("Credentials loaded from environment variables.")
        return username, password
    
    try:
        with open("credentials.json", "r", encoding="utf-8") as f:
            creds = json.load(f)
        print("Credentials loaded from credentials.json file.")
        return creds["username"], creds["password"]
    except FileNotFoundError:
        raise Exception("Credentials not found. Please set PIS_USERNAME/PIS_PASSWORD env vars or create credentials.json.")

def get_current_greek_time():
    """Get the current time in Greek timezone (UTC+3)."""
    return datetime.now(timezone.utc) + timedelta(hours=3)

def wait_until_absolute(target_dt_greece):
    """Wait until the target datetime (Greek time)."""
    print(f"🎯 Target event time (Greek): {target_dt_greece.strftime('%Y-%m-%d %H:%M:%S.%f')} EEST")
    while True:
        now = get_current_greek_time()
        if now >= target_dt_greece:
            print(f"✅ Target time reached: {now.strftime('%Y-%m-%d %H:%M:%S.%f')} EEST")
            break
        wait_sec = (target_dt_greece - now).total_seconds()
        print(f"Waiting {wait_sec:.1f} seconds until {target_dt_greece.strftime('%Y-%m-%d %H:%M:%S')} Greek time...")
        time.sleep(min(wait_sec, 30)) # Sleep max 30 seconds to re-check time regularly

def perform_login(page, username, password):
    """Performs the login steps and verifies success."""
    print("Navigating to login page...")
    try:
        page.goto(LOGIN_URL, timeout=PAGE_OPERATION_TIMEOUT_MS)
        page.wait_for_load_state("networkidle", timeout=PAGE_OPERATION_TIMEOUT_MS)

        print("Filling in login form...")
        # Use wait_for_selector for robustness in finding elements
        page.wait_for_selector('input[name="ctl00$MainContent$LoginUser$UserName"]', timeout=PAGE_OPERATION_TIMEOUT_MS).fill(username)
        page.wait_for_selector('input[name="ctl00$MainContent$LoginUser$Password"]', timeout=PAGE_OPERATION_TIMEOUT_MS).fill(password)
        
        # Click the login button and wait for navigation
        with page.expect_navigation(timeout=PAGE_OPERATION_TIMEOUT_MS):
            page.click('input[name="ctl00$MainContent$LoginUser$LoginButton"]')
        
        page.wait_for_load_state("networkidle", timeout=PAGE_OPERATION_TIMEOUT_MS)
        
        # Verify login success by checking for the welcome name or logout link
        login_success = False
        try:
            welcome_span = page.query_selector("#HeadLoginView_HeadLoginName")
            if welcome_span and welcome_span.is_visible(): # Ensure it's visible
                welcome_text = welcome_span.inner_text().strip()
                print(f"Found welcome name: {welcome_text}")
                login_success = True
        except PlaywrightError:
            pass # Ignore if selector not found, try fallback

        if not login_success:
            try:
                # Check for the Greek "Έξοδος" (Logout) link
                logout_link = page.query_selector("#HeadLoginView_HeadLoginStatus")
                if logout_link and logout_link.is_visible() and logout_link.inner_text().strip() == "Έξοδος":
                    print("Found 'Έξοδος' link, login probably successful.")
                    login_success = True
            except PlaywrightError:
                pass # Ignore if selector not found

        if not login_success:
            print("Login verification failed. Current page content:")
            with open("login_failed_response.html", "w", encoding="utf-8") as f:
                f.write(page.content())
            print("Login response saved to login_failed_response.html for inspection.")
            return False
        
        print("✅ Login successful!")
        return True

    except PlaywrightTimeoutError as e:
        print(f"❌ Playwright timeout during login: {e}")
        return False
    except PlaywrightError as e:
        print(f"❌ Playwright error during login: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error during login: {e}")
        return False

def download_assets(page, page_html, asset_dir):
    """
    Parses HTML for assets (PDFs, images) and downloads them.
    Uses page.request.get for binary content.
    """
    try:
        soup = BeautifulSoup(page_html, "html.parser")
        os.makedirs(asset_dir, exist_ok=True)
        
        asset_urls_to_download = set() 
        
        # Collect PDF links
        for a_tag in soup.find_all("a", href=True):
            if a_tag["href"].lower().endswith(".pdf"):
                asset_urls_to_download.add(a_tag["href"])
        
        # Collect image links (header.png, calendar.gif etc.)
        for img_tag in soup.find_all("img", src=True):
            asset_urls_to_download.add(img_tag["src"])

        if not asset_urls_to_download:
            print("  No new assets (PDFs/images) found on this page.")
            return

        print(f"  Found {len(asset_urls_to_download)} potential assets to download.")

        for asset_relative_url in asset_urls_to_download:
            # Construct absolute URL
            if asset_relative_url.startswith("/"):
                asset_full_url = "https://myrequests.pis.gr" + asset_relative_url
            elif not (asset_relative_url.startswith("http://") or asset_relative_url.startswith("https://")):
                # Handle other relative paths (e.g., "Styles/Site.css")
                # This might need more sophisticated base URL resolution if not directly in root
                base_url_parsed = page.url.split('?')[0].rsplit('/', 1)[0] # Get base path of current URL
                asset_full_url = f"{base_url_parsed}/{asset_relative_url}"
            else:
                asset_full_url = asset_relative_url # Already absolute

            # Clean up asset name from URL (remove query params and fragments)
            asset_name = os.path.basename(asset_full_url.split("?")[0].split('#')[0])
            if not asset_name or asset_name == '/':
                print(f"  Skipping asset with invalid name: {asset_full_url}")
                continue

            asset_path = os.path.join(asset_dir, asset_name)
            
            # Ensure unique file names if multiple assets have the same base name but different paths/timestamps
            counter = 0
            original_asset_path = asset_path
            while os.path.exists(asset_path):
                counter += 1
                name, ext = os.path.splitext(original_asset_path)
                asset_path = f"{name}_{counter}{ext}"

            try:
                # Use Playwright's page.request.get() for efficient binary download
                # This makes a direct HTTP request using the browser's session/cookies
                response = page.request.get(asset_full_url, timeout=PAGE_OPERATION_TIMEOUT_MS)
                if response.ok:
                    with open(asset_path, "wb") as af: # Use "wb" for binary write
                        af.write(response.body()) # Use response.body() for binary content
                    print(f"  Downloaded asset: {asset_path}")
                else:
                    print(f"  ❌ Failed to download asset {asset_full_url}: HTTP {response.status} {response.status_text}")
            except (PlaywrightTimeoutError, PlaywrightError) as asset_dl_err:
                print(f"  ❌ Playwright error downloading asset {asset_full_url}: {asset_dl_err}")
            except Exception as asset_other_err:
                print(f"  ❌ Other error downloading asset {asset_full_url}: {asset_other_err}")

    except Exception as soup_err:
        print(f"❌ Error processing HTML for assets: {soup_err}")

# --- Main Scraper Function ---

def run_scraper():
    """
    Logs in, waits until the target time, then repeatedly downloads the applications page
    for a set duration, saving each successful capture and associated assets.
    Continues until MIN_SUCCESS_SAVES are achieved or max attempts/duration reached.
    """
    start_overall_time = time.time()
    username, password = load_credentials()

    # Calculate the absolute target event time in Greek timezone
    target_event_time_greece = datetime(
        EVENT_YEAR, EVENT_MONTH, EVENT_DAY, EVENT_HOUR, EVENT_MINUTE, EVENT_SECOND, EVENT_MICROSECOND,
        tzinfo=timezone.utc # Start with UTC and then add timedelta
    ) + timedelta(hours=3)

    successful_saves_count = 0
    scrape_attempt_counter = 0

    with sync_playwright() as p:
        browser = None # Initialize browser to None for finally block
        try:
            browser = p.chromium.launch(headless=True)
            context = browser.new_context()
            page = context.new_page()

            # --- Phase 1: Initial Login ---
            print("\n--- Phase 1: Initial Login ---")
            if not perform_login(page, username, password):
                print("Initial login failed. Exiting bot.")
                return

            # --- Phase 2: Navigate to Applications Page and Wait for Event Time ---
            print("\n--- Phase 2: Navigating to Applications Page & Waiting for Event ---")
            try:
                page.goto(APPLICATIONS_URL, timeout=PAGE_OPERATION_TIMEOUT_MS)
                page.wait_for_load_state("networkidle", timeout=PAGE_OPERATION_TIMEOUT_MS)
                print(f"Pre-loaded applications page: {page.url}")
            except PlaywrightTimeoutError as e:
                print(f"❌ Timeout navigating to applications page after login: {e}")
                print("Attempting to re-login and retry navigation...")
                if perform_login(page, username, password): # Try re-login
                    page.goto(APPLICATIONS_URL, timeout=PAGE_OPERATION_TIMEOUT_MS) # Retry navigation
                    page.wait_for_load_state("networkidle", timeout=PAGE_OPERATION_TIMEOUT_MS)
                    print("Re-login and navigation successful.")
                else:
                    print("Re-login and navigation failed. Exiting bot.")
                    return
            except PlaywrightError as e:
                print(f"❌ Playwright error navigating to applications page: {e}. Exiting bot.")
                return

            # Wait until the precise target time
            wait_until_absolute(target_event_time_greece)

            # --- Phase 3: Aggressive Refreshing and Saving ---
            print("\n--- Phase 3: Aggressive Refreshing and Saving ---")
            loop_start_time = time.time() # Start timer for the scraping window

            while successful_saves_count < MIN_SUCCESS_SAVES and \
                  scrape_attempt_counter < MAX_SCRAPE_LOOP_ATTEMPTS and \
                  (time.time() - loop_start_time) < SCRAPE_WINDOW_DURATION_SECONDS:
                
                scrape_attempt_counter += 1
                print(f"\n--- Scrape Attempt {scrape_attempt_counter} ---")
                
                try:
                    # Check for session invalidation (redirected back to login page)
                    if page.url == LOGIN_URL or "Έξοδος" not in page.content(timeout=5000): # Check for logout link absence
                        print("Session invalidated during scrape loop! Attempting to re-login...")
                        if perform_login(page, username, password):
                            print("Re-login successful. Navigating back to applications page.")
                            page.goto(APPLICATIONS_URL, timeout=PAGE_OPERATION_TIMEOUT_MS)
                            page.wait_for_load_state("networkidle", timeout=PAGE_OPERATION_TIMEOUT_MS)
                        else:
                            print("Re-login failed. Cannot continue scraping. Breaking loop.")
                            break # Critical failure, stop trying

                    # Reload the page to get the latest content
                    print(f"Reloading page for new data (attempt {scrape_attempt_counter})...")
                    page.reload(timeout=PAGE_OPERATION_TIMEOUT_MS)
                    page.wait_for_load_state("networkidle", timeout=PAGE_OPERATION_TIMEOUT_MS)

                    # Get and save the HTML content
                    page_html = page.content()
                    current_greek_time = get_current_greek_time()
                    ts = current_greek_time.strftime("%Y%m%d_%H%M%S_%f") # Add microseconds for uniqueness
                    fname = f"application_view_{ts}.html"
                    
                    with open(fname, "w", encoding="utf-8") as f:
                        f.write(page_html)
                    
                    successful_saves_count += 1 # Increment only after successful HTML save
                    print(f"  ✅ Saved main HTML: {fname}. Successful HTML saves: {successful_saves_count}/{MIN_SUCCESS_SAVES}")

                    # --- New Data Detection (Customize this part!) ---
                    # You need to define what "new info" looks like.
                    # Example: looking for a specific text, a new table row, or a new PDF link timestamp.
                    # For now, a placeholder check:
                    if "ΝΕΑ ΑΙΤΗΣΗ" in page_html: # Example: check for a specific new text
                        print("  🎉 'ΝΕΑ ΑΙΤΗΣΗ' (New Application) text found in this saved page!")
                    else:
                        print("  New data not detected in this saved page yet.")

                    # Download associated assets (PDFs, images)
                    download_assets(page, page_html, "application_assets")

                except (PlaywrightTimeoutError, PlaywrightError) as e:
                    print(f"❌ Playwright error during scrape attempt {scrape_attempt_counter}: {e}")
                    # Save a debug HTML if a Playwright error occurs during the loop
                    try:
                        debug_fname = f"error_page_{ts}_playwright_error.html"
                        with open(debug_fname, "w", encoding="utf-8") as f:
                            f.write(page.content())
                        print(f"  Saved error page to {debug_fname} for inspection.")
                    except Exception as debug_e:
                        print(f"  Could not save debug page: {debug_e}")
                except Exception as e:
                    print(f"❌ Unexpected error during scrape attempt {scrape_attempt_counter}: {e}")
                    # Save a debug HTML for other unexpected errors
                    try:
                        debug_fname = f"error_page_{ts}_unexpected_error.html"
                        with open(debug_fname, "w", encoding="utf-8") as f:
                            f.write(page.content())
                        print(f"  Saved error page to {debug_fname} for inspection.")
                    except Exception as debug_e:
                        print(f"  Could not save debug page: {debug_e}")

                # Calculate remaining time for this interval and sleep
                time_elapsed_in_interval = time.time() - (loop_start_time + (scrape_attempt_counter - 1) * SCRAPE_INTERVAL_SECONDS)
                sleep_duration = SCRAPE_INTERVAL_SECONDS - time_elapsed_in_interval
                if sleep_duration > 0:
                    time.sleep(sleep_duration)

            if successful_saves_count >= MIN_SUCCESS_SAVES:
                print(f"\n✅ Successfully saved {successful_saves_count} application pages (goal: {MIN_SUCCESS_SAVES}).")
            else:
                print(f"\n⚠️ Loop finished. Could not achieve {MIN_SUCCESS_SAVES} successful saves within limits. Total saved: {successful_saves_count}")

        except Exception as e:
            print(f"❌ An unhandled error occurred in the main scraper function: {e}")
        finally:
            if browser:
                browser.close()
                print("Browser closed.")

    end_overall_time = time.time()
    elapsed_overall = end_overall_time - start_overall_time
    print(f"⏱️ Total script execution time: {elapsed_overall:.2f} seconds.")

if __name__ == "__main__":
    print("Starting the web scraping process with Playwright...")
    run_scraper()
    print("Scraping process finished.")
