import os
import json
import smtplib
import zipfile
from email.message import EmailMessage

ARTIFACTS_GLOB = '*.html'
ZIP_NAME = 'pis-gr-scraper-html.zip'
SMTP_ENV_VARS = ['SMTP_USERNAME', 'SMTP_PASSWORD']
SMTP_JSON = 'smtp.json'

# Find SMTP credentials
smtp_username = os.environ.get('SMTP_USERNAME')
smtp_password = os.environ.get('SMTP_PASSWORD')
if smtp_username and smtp_password:
    print('SMTP credentials loaded from environment variables.')
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', 465))
    receiver = os.environ.get('SMTP_RECEIVER', 'isidora.k1708@gmail.com')
else:
    with open(SMTP_JSON, 'r', encoding='utf-8') as f:
        smtp_conf = json.load(f)
    smtp_server = smtp_conf['smtp_server']
    smtp_port = int(smtp_conf['smtp_port'])
    smtp_username = smtp_conf['smtp_username']
    smtp_password = smtp_conf['smtp_password']
    receiver = smtp_conf['receiver']

# Zip artifacts
import glob
artifact_files = glob.glob(ARTIFACTS_GLOB)
if not artifact_files:
    print('No HTML artifacts found to send.')
    exit(0)
if not os.path.exists(ZIP_NAME):
    with zipfile.ZipFile(ZIP_NAME, 'w') as zipf:
        for fname in artifact_files:
            zipf.write(fname)
    print(f'Artifacts zipped to {ZIP_NAME}')
else:
    print(f'Using existing zip: {ZIP_NAME}')

# Send email
msg = EmailMessage()
msg['Subject'] = 'PIS-GR Scraper Artifacts'
msg['From'] = smtp_username
msg['To'] = receiver
msg.set_content('See attached HTML artifacts from PIS-GR scraper.')
with open(ZIP_NAME, 'rb') as f:
    msg.add_attachment(f.read(), maintype='application', subtype='zip', filename=ZIP_NAME)

try:
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
    print('Email sent successfully.')
except Exception as e:
    print(f'Failed to send email: {e}')
