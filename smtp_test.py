import json
import smtplib
from email.message import EmailMessage

with open('smtp.json', 'r', encoding='utf-8') as f:
    smtp_conf = json.load(f)

smtp_server = smtp_conf['smtp_server']
smtp_port = int(smtp_conf['smtp_port'])
smtp_username = smtp_conf['smtp_username']
smtp_password = smtp_conf['smtp_password']

msg = EmailMessage()
msg['Subject'] = 'SMTP Test'
msg['From'] = smtp_username
msg['To'] = smtp_username
msg.set_content('This is a test email to verify SMTP credentials.')

try:
    with smtplib.SMTP_SSL(smtp_server, smtp_port) as server:
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
    print('✅ Test email sent successfully.')
except Exception as e:
    print(f'❌ Failed to send test email: {e}')
