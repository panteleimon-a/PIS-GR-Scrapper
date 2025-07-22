# PIS-GR Scraper

This project automates the login and data scraping process for the Greek PIS portal for getting doctor applicant's number using Python and Playwright. Help your graduate friends get into the wanna-be-doctor queue by using this bot.

## Features
- Logs in to https://myrequests.pis.gr/ with provided credentials
- Waits until a scheduled Greek time (14:00 UTC+3) before scraping
- Downloads the applications page every 5 seconds for 1 minute, saving each HTML snapshot
- Robust error handling and logging
- Can be run locally or via GitHub Actions (see workflow in `.github/workflows/python-app.yml`)

## Requirements
- Python 3.8+
- Playwright for Python
- Google Chrome or Chromium (Playwright will install browsers automatically)

## Installation
1. Clone this repository.
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   python -m playwright install
   ```

## Usage
### 1. Credentials
You must provide your PIS portal credentials. You can do this in one of two ways:
- Set environment variables `PIS_USERNAME` and `PIS_PASSWORD` (recommended for CI)
- Or, create a `credentials.json` file in the project root:
  ```json
  {
    "username": "YOUR_USERNAME",
    "password": "YOUR_PASSWORD"
  }
  ```
  Supports Unicode (Greek) characters.

### 2. Run the Bot
```sh
python bot.py
```

### 3. Output
- On success, HTML files named `application_view_YYYYMMDD_HHMMSS.html` will be saved.
- If login fails, `login_failed_response.html` will be saved for debugging.

## GitHub Actions
- The workflow in `.github/workflows/python-app.yml` allows scheduled or manual runs.
- Set repository secrets `PIS_USERNAME` and `PIS_PASSWORD` for CI.
- Artifacts (HTML files) are uploaded after each run.

## Disclaimer
This script is for educational purposes only. Use responsibly and in accordance with the website's Terms of Service. The author is not responsible for misuse, account restrictions, or IP bans.

## License
MIT License
