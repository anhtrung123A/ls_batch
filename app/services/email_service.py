import html
import smtplib
from email.mime.text import MIMEText

from app.infrastructure.config import Settings


class EmailService:
    def __init__(self, settings: Settings):
        self.settings = settings

    def send_student_created(self, to_email: str, full_name: str, password: str, student_code: str):
        if not self.settings.smtp_host or not self.settings.smtp_from_email:
            raise RuntimeError("SMTP settings are not configured.")

        body = self._build_student_created_html(
            full_name=full_name,
            email=to_email,
            password=password,
            student_code=student_code,
        )
        message = MIMEText(body, "html", "utf-8")
        message["Subject"] = "Your student account is ready"
        message["From"] = self.settings.smtp_from_email
        message["To"] = to_email

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as client:
            client.sendmail(self.settings.smtp_from_email, [to_email], message.as_string())

    def send_payroll_generated(
        self,
        to_email: str,
        full_name: str,
        month: int,
        year: int,
        base_amount: str,
        teaching_amount: str,
        kpi_amount: str,
        gross_amount: str,
        net_amount: str,
    ):
        if not self.settings.smtp_host or not self.settings.smtp_from_email:
            raise RuntimeError("SMTP settings are not configured.")

        body = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Monthly Payroll</title>
</head>
<body style="font-family: Times New Roman; color: #222;">
  <h2>Monthly Payroll</h2>
  <p>Hello {html.escape(full_name)},</p>
  <p>Your payroll for <strong>{month:02d}/{year}</strong> has been generated.</p>
  <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; min-width: 420px;">
    <thead>
      <tr style="background: #f4f4f4;">
        <th align="left">Component</th>
        <th align="right">Amount</th>
      </tr>
    </thead>
    <tbody>
      <tr>
        <td>Base salary</td>
        <td align="right">{html.escape(base_amount)}</td>
      </tr>
      <tr>
        <td>Teaching amount</td>
        <td align="right">{html.escape(teaching_amount)}</td>
      </tr>
      <tr>
        <td>KPI amount</td>
        <td align="right">{html.escape(kpi_amount)}</td>
      </tr>
      <tr style="font-weight: bold;">
        <td>Gross amount</td>
        <td align="right">{html.escape(gross_amount)}</td>
      </tr>
      <tr style="font-weight: bold;">
        <td>Net amount</td>
        <td align="right">{html.escape(net_amount)}</td>
      </tr>
    </tbody>
  </table>
  <p>Best regards,<br>LinguaSync Team</p>
</body>
</html>"""

        message = MIMEText(body, "html", "utf-8")
        message["Subject"] = f"Payroll {month:02d}/{year}"
        message["From"] = self.settings.smtp_from_email
        message["To"] = to_email

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as client:
            client.sendmail(self.settings.smtp_from_email, [to_email], message.as_string())

    @staticmethod
    def _build_student_created_html(full_name: str, email: str, password: str, student_code: str) -> str:
        return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Student Account Created</title>
</head>
<body style="font-family: Times New Roman; color: #222;">
  <h2>Welcome to LinguaSync</h2>
  <p>Hello {html.escape(full_name)},</p>
  <p>Your student account has been created successfully.</p>
  <p><strong>Student code:</strong> {html.escape(student_code)}</p>
  <p><strong>Email:</strong> {html.escape(email)}</p>
  <p><strong>Temporary password:</strong> {html.escape(password)}</p>
  <p>Please log in and change your password as soon as possible.</p>
  <p>Best regards,<br>LinguaSync Team</p>
</body>
</html>"""
