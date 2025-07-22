# -*- coding: utf-8 -*-
import os
import base64
import json
import time
import sys
from datetime import datetime, timedelta, timezone
from playwright.sync_api import sync_playwright

def flush_print(*args, **kwargs):
    print(*args, **kwargs)
    sys.stdout.flush()

def load_credentials():
    username = os.environ.get("PIS_USERNAME")
    password = os.environ.get("PIS_PASSWORD")
    username_b64 = os.environ.get("PIS_USERNAME_B64")
    if username_b64:
        username = base64.b64decode(username_b64).decode("utf-8")
    if username and password:
        flush_print("Credentials loaded from environment variables.")
        return username, password
    try:
        with open("credentials.json", "r", encoding="utf-8") as f:
            creds = json.load(f)
        flush_print("Credentials loaded from credentials.json file.")
        return creds["username"], creds["password"]
    except FileNotFoundError:
        raise Exception("Credentials not found. Please set PIS_USERNAME/PIS_PASSWORD env vars or create credentials.json.")

def get_greek_time():
    return datetime.now(timezone.utc) + timedelta(hours=3)

def wait_until(target_dt):
    while True:
        now = get_greek_time()
        if now >= target_dt:
            break
        wait_sec = (target_dt - now).total_seconds()
        flush_print(f"Waiting {wait_sec:.1f} seconds until {target_dt.strftime('%Y-%m-%d %H:%M:%S')} Greek time...")
        time.sleep(min(wait_sec, 30))

def run_scraper():
    flush_print("=== Script started ===")
    start_time = time.time()
    username, password = load_credentials()
    login_url = "https://myrequests.pis.gr/Account/Login.aspx"
    applications_url = "https://myrequests.pis.gr/Applications.aspx"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        flush_print("Navigating to login page...")
        page.goto(login_url)
        flush_print("Filling in login form...")
        page.fill('input[name="ctl00$MainContent$LoginUser$UserName"]', username)
        page.fill('input[name="ctl00$MainContent$LoginUser$Password"]', password)
        page.click('input[name="ctl00$MainContent$LoginUser$LoginButton"]')
        flush_print("Waiting for login to complete...")
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        content = page.content()
        login_success = False
        try:
            welcome_span = page.query_selector("#HeadLoginView_HeadLoginName")
            if welcome_span:
                welcome_text = welcome_span.inner_text().strip()
                flush_print(f"Found welcome name: {welcome_text}")
                login_success = True
        except Exception as e:
            flush_print(f"Could not find welcome span: {e}")
        if not login_success:
            try:
                logout_link = page.query_selector("#HeadLoginView_HeadLoginStatus")
                if logout_link:
                    flush_print("Found logout link, login probably successful.")
                    login_success = True
            except Exception as e:
                flush_print(f"Could not find logout link: {e}")

        if login_success:
            # Wait until Tuesday, 29/7/2025, 13:55 Greek time before proceeding
            scheduled_start = datetime(2025, 7, 29, 13, 55, 0, tzinfo=timezone(timedelta(hours=3)))
            now = get_greek_time()
            if now < scheduled_start:
                flush_print(f"Waiting {(scheduled_start - now).total_seconds():.1f} seconds until scheduled start at {scheduled_start.strftime('%Y-%m-%d %H:%M:%S')} Greek time...")
                wait_until(scheduled_start)
            flush_print("✅ Scheduled start reached. Navigating to applications page and waiting for 14:00 Greek time...")
            page.goto(applications_url)
            page.wait_for_load_state("networkidle")
            greek_now = get_greek_time()
            target_time = greek_now.replace(hour=14, minute=0, second=0, microsecond=0)
            if greek_now >= target_time:
                flush_print("It's already 14:00 or later Greek time, starting immediately.")
            else:
                wait_until(target_time)
            loop_start = time.time()
            duration = 60
            interval = 5
            count = 0
            while True:
                now = time.time()
                if now - loop_start > duration:
                    break
                greek_now = get_greek_time()
                ts = greek_now.strftime("%Y%m%d_%H%M%S")
                fname = f"application_view_{ts}.html"
                flush_print(f"Saving {fname}")
                with open(fname, "w", encoding="utf-8") as f:
                    f.write(page.content())
                count += 1
                if now - loop_start + interval > duration:
                    break
                time.sleep(interval)
                page.reload()
                page.wait_for_load_state("networkidle")
            flush_print(f"✅ Finished repeated downloads. Total pages saved: {count}")
        else:
            flush_print("Login likely failed. Check credentials or form data.")
            with open("login_failed_response.html", "w", encoding="utf-8") as f:
                f.write(content)
            flush_print("Login response saved to login_failed_response.html for inspection.")

        browser.close()
    end_time = time.time()
    elapsed = end_time - start_time
    flush_print(f"⏱️ Total time taken: {elapsed:.2f} seconds.")

if __name__ == "__main__":
    flush_print("Starting the web scraping process with Playwright...")
    run_scraper()
    flush_print("Scraping process finished.")
