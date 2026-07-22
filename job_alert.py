import json
import os
import smtplib
from pathlib import Path
from email.mime.text import MIMEText

import requests


# החברות שהקוד בודק
companies = ["payoneer", "riskified", "taboola", "similarweb", "melio"]

# הפרטים יגיעו מ-GitHub Secrets, ולא יהיו גלויים בקוד
sender_email = os.environ["SENDER_EMAIL"]
app_password = os.environ["APP_PASSWORD"]
recipient_email = os.environ["RECIPIENT_EMAIL"]

# הקובץ שבו תישמר רשימת המשרות שכבר נבדקו
sent_jobs_file = Path("sent_jobs.json")


def send_email(subject, body):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = recipient_email

    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(sender_email, app_password)
        server.send_message(msg)


# איסוף כל משרות ה-Analyst שמפורסמות כרגע
current_jobs = {}

for company in companies:
    try:
        response = requests.get(
            f"https://boards-api.greenhouse.io/v1/boards/{company}/jobs",
            timeout=30
        )
        response.raise_for_status()
        data = response.json()

    except requests.RequestException as error:
        print(f"Could not check {company}: {error}")
        continue

    for job in data.get("jobs", []):
        title = job.get("title", "")

        if "analyst" in title.lower():
            job_key = f"{company} | {title}"
            current_jobs[job_key] = job.get("absolute_url", "")


# קריאת המשרות שכבר נשמרו בהרצות הקודמות
if sent_jobs_file.exists():
    saved_data = json.loads(
        sent_jobs_file.read_text(encoding="utf-8")
    )
    sent_jobs = set(saved_data)
else:
    sent_jobs = set()


# מציאת המשרות שלא הופיעו ברשימה הקודמת
new_jobs = {
    job: link
    for job, link in current_jobs.items()
    if job not in sent_jobs
}


# בהרצה הראשונה רק יוצרים נקודת התחלה, בלי לשלוח את כל המשרות שוב
if not sent_jobs:
    print("First run: existing jobs saved.")

elif new_jobs:
    email_lines = []

    for job, link in new_jobs.items():
        email_lines.append(job)

        if link:
            email_lines.append(link)

        email_lines.append("")

    email_text = "\n".join(email_lines)

    send_email("New Job Postings", email_text)
    print(f"Email sent with {len(new_jobs)} new job(s).")

else:
    print("No new jobs.")


# שמירת כל המשרות הנוכחיות לקראת ההרצה הבאה
sent_jobs_file.write_text(
    json.dumps(
        sorted(current_jobs.keys()),
        ensure_ascii=False,
        indent=2
    ),
    encoding="utf-8"
)
