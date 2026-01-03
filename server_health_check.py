import json
import sys
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

# ================= CONFIG =================
TIMEOUT = 5
DEFAULT_ENV_FILES = ["local.json", "dev.json", "stage.json"]

SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "alert@example.com"
SMTP_PASS = "APP_PASSWORD"
FROM_EMAIL = "alert@example.com"
# ==========================================


def load_config(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


def is_server_up(url):
    try:
        requests.head(url, timeout=TIMEOUT, verify=False)
        return True, None
    except requests.exceptions.RequestException as e:
        return False, str(e)


def generate_table(category, rows):
    if not rows:
        return ""

    title = category.replace("_", " ").upper()
    table_rows = ""

    for row in rows:
        table_rows += f"""
        <tr>
            <td>{row['name']}</td>
            <td>{row['url']}</td>
            <td style="color:red;">{row['error']}</td>
            <td>{row['time']}</td>
        </tr>
        """

    return f"""
    <h3>{title}</h3>
    <table border="1" cellpadding="8" cellspacing="0"
           style="border-collapse:collapse;width:100%;">
        <tr style="background:#f2f2f2;">
            <th>Server Name</th>
            <th>URL</th>
            <th>Error</th>
            <th>Checked At</th>
        </tr>
        {table_rows}
    </table>
    <br/>
    """


def build_html_email(env, grouped_failures):
    subject = f"[ALERT] {env} ENV | Server Down Report"

    body_sections = ""
    for category, rows in grouped_failures.items():
        body_sections += generate_table(category, rows)

    html_body = f"""
    <html>
    <body style="font-family: Arial, sans-serif;">
        <h2 style="color:red;">🚨 Server Down Alert</h2>
        <p><b>Environment:</b> {env}</p>
        {body_sections}
        <p>Please investigate and restore the services.</p>
        <p><b>Server Monitoring System</b></p>
    </body>
    </html>
    """

    return subject, html_body


def send_email(recipients, subject, html_body):
    msg = MIMEMultipart()
    msg["From"] = FROM_EMAIL
    msg["To"] = ", ".join(recipients)
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        server.sendmail(FROM_EMAIL, recipients, msg.as_string())


def process_environment(env_file):
    config = load_config(env_file)
    environment = config.get("environment", Path(env_file).stem.upper())

    grouped_failures = {}
    recipients = set()

    for category, servers in config.items():
        if category == "environment":
            continue

        for server in servers:
            is_up, error = is_server_up(server["url"])

            if not is_up:
                grouped_failures.setdefault(category, []).append({
                    "name": server["name"],
                    "url": server["url"],
                    "error": error,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })
                recipients.update(server["emails"])

    if grouped_failures:
        subject, html_body = build_html_email(environment, grouped_failures)
        send_email(list(recipients), subject, html_body)
        print(f"📧 Alert sent for {environment}")
    else:
        print(f"✅ All servers UP in {environment}. No email sent.")


def main():
    # Case 1: specific env
    if len(sys.argv) == 2:
        process_environment(sys.argv[1])
        return

    # Case 2: all envs
    for env_file in DEFAULT_ENV_FILES:
        if Path(env_file).exists():
            process_environment(env_file)


if __name__ == "__main__":
    main()
