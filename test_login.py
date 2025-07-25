import json
from playwright.sync_api import sync_playwright

def load_credentials():
    with open("credentials.json", "r", encoding="utf-8") as f:
        creds = json.load(f)
    return creds["username"], creds["password"]

def test_login():
    username, password = load_credentials()
    login_url = "https://myrequests.pis.gr/Account/Login.aspx"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        page.goto(login_url)
        page.fill('input[name="ctl00$MainContent$LoginUser$UserName"]', username)
        page.fill('input[name="ctl00$MainContent$LoginUser$Password"]', password)
        page.click('input[name="ctl00$MainContent$LoginUser$LoginButton"]')
        page.wait_for_load_state("networkidle")
        page.wait_for_timeout(2000)

        # Check for login success by presence of welcome name or logout link
        login_success = False
        try:
            welcome_span = page.query_selector("#HeadLoginView_HeadLoginName")
            if welcome_span and welcome_span.inner_text().strip():
                print("✅ Login successful. Welcome:", welcome_span.inner_text().strip())
                login_success = True
        except Exception as e:
            print("Could not find welcome span:", e)

        if not login_success:
            try:
                logout_link = page.query_selector("#HeadLoginView_HeadLoginStatus")
                if logout_link:
                    print("✅ Login probably successful (logout link found).")
                    login_success = True
            except Exception as e:
                print("Could not find logout link:", e)

        if not login_success:
            print("❌ Login failed. Saving response for inspection.")
            with open("login_failed_response.html", "w", encoding="utf-8") as f:
                f.write(page.content())

        browser.close()

if __name__ == "__main__":
    test_login()