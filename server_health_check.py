import json
import sys
import requests
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path
import urllib3

# ================= GLOBAL CONFIG =================
TIMEOUT = 5
DEFAULT_ENV_FILES = ["local.json", "dev.json", "stage.json"]

# SMTP CONFIG (CHANGE AS NEEDED)
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = "alert@example.com"
SMTP_PASS = "APP_PASSWORD"
FROM_EMAIL = "alert@example.com"
# =================================================

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# ---------- UTILS ----------
def load_config(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


def is_server_up(url):
    """
    Server-level check only.
    Any HTTP response => server UP
    Exceptions => server DOWN
    """
    try:
        response = requests.head(url, timeout=TIMEOUT, verify=False)
        return True, str(response.status_code)
    except requests.exceptions.RequestException as e:
        return False, e


def classify_error(error):
    """
    Convert raw errors into user-friendly messages + severity + color
    """
    if error is None:
        return "OK", "Server is running", "#4CAF50"

    err = str(error).lower()

    if "connection refused" in err:
        return "CRITICAL", "Server is DOWN (connection refused)", "#d32f2f"

    if "timeout" in err:
        return "CRITICAL", "Server is DOWN (request timeout)", "#d32f2f"

    if "name or service not known" in err or "dns" in err:
        return "CRITICAL", "Server is DOWN (DNS resolution failed)", "#d32f2f"

    if "ssl" in err:
        return "CRITICAL", "Server is DOWN (SSL handshake error)", "#d32f2f"

    if err.isdigit():
        status = int(err)
        if status == 404:
            return "WARNING", "Endpoint not found (404)", "#f57c00"
        if status in (401, 403):
            return "WARNING", "Unauthorized / Forbidden access", "#f57c00"
        if status >= 500:
            return "ERROR", "Server error (5xx)", "#d32f2f"

    return "ERROR", "Unknown server error", "#d32f2f"


# ---------- HTML BUILDERS ----------
def generate_table(category, rows):
    if not rows:
        return ""

    title = category.replace("_", " ").upper()
    table_rows = ""

    for row in rows:
        table_rows += f"""
        <tr style="background-color:{row['color']}; color:white;">
            <td>{row['name']}</td>
            <td>{row['url']}</td>
            <td>{row['severity']}</td>
            <td>{row['error']}</td>
            <td>{row['time']}</td>
        </tr>
        """

    return f"""
    <h3>{title}</h3>
    <table border="1" cellpadding="8" cellspacing="0"
           style="border-collapse:collapse;width:100%;">
        <tr style="background:#333;color:white;">
            <th>Server Name</th>
            <th>URL</th>
            <th>Severity</th>
            <th>Issue</th>
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
        <h2 style="color:#d32f2f;">🚨 Server Health Alert</h2>
        <p><b>Environment:</b> {env}</p>

        {body_sections}

        <p>
            <b>Severity Guide:</b><br/>
            🔴 CRITICAL – Server Down<br/>
            🟠 WARNING – Path / Access issue
        </p>

        <p>
            Regards,<br/>
            <b>Server Monitoring System</b>
        </p>
    </body>
    </html>
    """

    return subject, html_body


# ---------- EMAIL ----------
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


# ---------- CORE LOGIC ----------
def process_environment(env_file):
    config = load_config(env_file)
    environment = config.get("environment", Path(env_file).stem.upper())

    grouped_failures = {}
    recipients = set()

    for category, servers in config.items():
        if category == "environment":
            continue

        for server in servers:
            is_up, raw_error = is_server_up(server["url"])

            if not is_up:
                severity, friendly_error, color = classify_error(raw_error)

                grouped_failures.setdefault(category, []).append({
                    "name": server["name"],
                    "url": server["url"],
                    "severity": severity,
                    "error": friendly_error,
                    "color": color,
                    "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                })

                recipients.update(server["emails"])

    if grouped_failures:
        subject, html_body = build_html_email(environment, grouped_failures)
        send_email(list(recipients), subject, html_body)
        print(f"📧 Alert email sent for {environment}")
    else:
        print(f"✅ All servers UP in {environment}. No email sent.")


def main():
    # Case 1: Single environment
    if len(sys.argv) == 2:
        process_environment(sys.argv[1])
        return

    # Case 2: All environments
    for env_file in DEFAULT_ENV_FILES:
        if Path(env_file).exists():
            process_environment(env_file)


if __name__ == "__main__":
    main()
