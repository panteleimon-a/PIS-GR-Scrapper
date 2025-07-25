# -*- coding: utf-8 -*-
import os
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

# Removed credentials and time/datetime utilities for public asset parsing

def run_asset_parser():
    """
    Navigates to a test URL, parses for assets, downloads them, and verifies results.
    No time-based scheduling or delays.
    """
    test_url = "https://science.umd.edu/labs/delwiche/bsci348s/lec/Markov.htm"
    expected_files = [
        "ModelPlane1.jpg",
        "ModelPlane2.jpg",
        "main.html"
    ]
    asset_dir = "test_assets"

    # Initial cleanup of the directory from any previous runs
    if os.path.exists(asset_dir):
        for fname in os.listdir(asset_dir):
            fpath = os.path.join(asset_dir, fname)
            if os.path.isfile(fpath):
                os.remove(fpath)
        os.rmdir(asset_dir)
    os.makedirs(asset_dir, exist_ok=True)

    all_ok = True
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            context = browser.new_context()
            page = context.new_page()
            page.goto(test_url)
            page_html = page.content()

            soup = BeautifulSoup(page_html, "html.parser")
            asset_tags = soup.find_all("a", href=True) + soup.find_all("img", src=True)
            
            download_urls = set()
            for tag in asset_tags:
                relative_url = tag.get("href") or tag.get("src")
                if not relative_url:
                    continue
                
                absolute_url = urljoin(test_url, relative_url)

                if absolute_url.endswith(("main.html", ".jpg", ".pdf")):
                    download_urls.add(absolute_url)

            # Download assets
            for url in download_urls:
                asset_name = os.path.basename(url.split("?")[0])
                asset_path = os.path.join(asset_dir, asset_name)
                
                asset_page = context.new_page()
                response = asset_page.goto(url)
                
                if asset_name.endswith((".jpg", ".pdf")):
                    with open(asset_path, "wb") as f:
                        f.write(response.body())
                elif asset_name == "main.html":
                    with open(asset_path, "w", encoding="utf-8") as f:
                        f.write(response.text())
                        
                asset_page.close()
        finally:
            browser.close()

    # --- Assertions ---
    print("--- Verifying downloaded files ---")
    for fname in expected_files:
        if os.path.exists(os.path.join(asset_dir, fname)):
            print(f"✅ {fname} downloaded successfully.")
        else:
            print(f"❌ {fname} was not downloaded.")
            all_ok = False

    extra_files = [f for f in os.listdir(asset_dir) if f not in expected_files]
    if extra_files:
        print(f"❌ Unexpected files downloaded: {extra_files}")
        all_ok = False
    else:
        print("✅ No unexpected files downloaded.")

    # --- Cleanup ---
    if os.path.exists(asset_dir):
        try:
            for fname in os.listdir(asset_dir):
                fpath = os.path.join(asset_dir, fname)
                if os.path.isfile(fpath):
                    os.remove(fpath)
            os.rmdir(asset_dir)
            print(f"\n✅ Cleanup of '{asset_dir}' successful.")
        except Exception as cleanup_err:
            print(f"\n❌ Cleanup failed: {cleanup_err}. Please remove '{asset_dir}' manually.")

    if all_ok:
        print("\n✅ Asset parser test PASSED.")
    else:
        print("\n❌ Asset parser test FAILED.")

if __name__ == "__main__":
    print("Starting asset parser test...")
    run_asset_parser()
    print("Asset parser test finished.")
