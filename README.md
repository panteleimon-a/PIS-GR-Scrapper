# PIS-GR Scraper

A Python + Playwright automation tool for preparing and capturing the PIS application flow (`https://myrequests.pis.gr/`) around opening time.

> [!IMPORTANT]
> This tool assists with preparation and submission timing, but **you remain fully responsible** for your credentials, the correctness of your data, and final submission actions.

---

## What it does

- Logs into the PIS portal with your credentials
- Waits until the configured target time (Greek time / UTC+3 logic in code)
- Repeatedly captures the applications page and stores timestamped HTML snapshots
- Downloads related assets (PDF/images) into `application_assets/`
- Supports local execution and GitHub Actions execution

---

## Repository structure

- `/home/runner/work/PIS-GR-Scrapper/PIS-GR-Scrapper/bot.py` – original scraper entrypoint
- `/home/runner/work/PIS-GR-Scrapper/PIS-GR-Scrapper/test_bot.py` – hardened flow used by workflows
- `/home/runner/work/PIS-GR-Scrapper/PIS-GR-Scrapper/send_artifact_email.py` – optional artifact email sender
- `/home/runner/work/PIS-GR-Scrapper/PIS-GR-Scrapper/.github/workflows/python-app.yml` – CI/triggered run flow

---

## Requirements

- Python 3.8+
- Playwright for Python
- Chromium/Chrome (`python -m playwright install`)

Install:

```bash
pip install -r requirements.txt
python -m playwright install
```

---

## Credentials

Use one of the following:

1. Environment variables (recommended):
   - `PIS_USERNAME`
   - `PIS_PASSWORD`

2. Local file `/home/runner/work/PIS-GR-Scrapper/PIS-GR-Scrapper/credentials.json`:

```json
{
  "username": "YOUR_USERNAME",
  "password": "YOUR_PASSWORD"
}
```

---

## Run locally

```bash
python bot.py
```

(Workflows currently run `test_bot.py`.)

---

## Output

- `application_view_YYYYMMDD_HHMMSS.html` snapshots
- `application_assets/` downloaded assets
- `login_failed_response.html` on login failure

---

## GitHub Actions (easy trigger setup)

Workflows already include `workflow_dispatch`, so manual triggering is available in GitHub UI.

### One-time setup

1. Go to repository **Settings → Secrets and variables → Actions**
2. Add:
   - `PIS_USERNAME`
   - `PIS_PASSWORD`
3. (Optional) Add email secrets if you use artifact mailing:
   - `SMTP_USERNAME`
   - `SMTP_PASSWORD`

### Manual trigger (easiest for non-technical users)

1. Open **Actions** tab
2. Select **Python application** workflow
3. Click **Run workflow**

### Scheduled trigger

- Edit cron lines in `/home/runner/work/PIS-GR-Scrapper/PIS-GR-Scrapper/.github/workflows/python-app.yml`
- Commit the new schedule

---

## Can this become a platform people use?

Yes. A practical path:

1. **Stabilize config**
   - Move target date/time and run options into environment variables
   - Keep credentials in encrypted storage only

2. **Add a simple user-facing trigger UI**
   - Small web app (e.g., FastAPI + basic HTML form)
   - User enters timing + notification preferences
   - Backend triggers GitHub Actions or a job queue

3. **Add safe multi-user architecture**
   - Per-user encrypted secrets
   - Isolated runs (one browser context per job)
   - Audit logs and failure notifications

4. **Make setup almost zero-friction**
   - “Connect GitHub” flow or hosted dashboard
   - One-click “Run now” and “Schedule run” buttons
   - Default templates for common opening-time scenarios

If you want, the next step can be a minimal implementation plan for:
- **Option A:** “no-server” approach using only GitHub Actions inputs
- **Option B:** small hosted dashboard with one-click trigger.

---

## Disclaimer

Use responsibly and in accordance with PIS website terms and applicable law. The maintainers are not responsible for misuse, account restrictions, or service-side policy violations.

## License

MIT License
