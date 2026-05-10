import html
import smtplib
from email.mime.text import MIMEText
from pathlib import Path

from app.infrastructure.config import Settings


class EmailService:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.template_dir = Path(__file__).resolve().parents[1] / "views" / "templates"

    def send_student_created(self, to_email: str, full_name: str, password: str, student_code: str):
        self._ensure_smtp_configured()
        body = self._render_template(
            "student_created.html",
            {
                "FULL_NAME": html.escape(full_name),
                "EMAIL": html.escape(to_email),
                "PASSWORD": html.escape(password),
                "STUDENT_CODE": html.escape(student_code),
            },
        )
        self._send_email(to_email, "Your student account is ready", body)

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
        self._ensure_smtp_configured()
        body = self._render_template(
            "payroll_generated.html",
            {
                "FULL_NAME": html.escape(full_name),
                "MONTH_YEAR": f"{month:02d}/{year}",
                "BASE_AMOUNT": html.escape(base_amount),
                "TEACHING_AMOUNT": html.escape(teaching_amount),
                "KPI_AMOUNT": html.escape(kpi_amount),
                "GROSS_AMOUNT": html.escape(gross_amount),
                "NET_AMOUNT": html.escape(net_amount),
            },
        )
        self._send_email(to_email, f"Payroll {month:02d}/{year}", body)

    def _ensure_smtp_configured(self):
        if not self.settings.smtp_host or not self.settings.smtp_from_email:
            raise RuntimeError("SMTP settings are not configured.")

    def _render_template(self, template_name: str, mapping: dict[str, str]) -> str:
        template_path = self.template_dir / template_name
        content = template_path.read_text(encoding="utf-8")
        for key, value in mapping.items():
            content = content.replace(f"{{{{{key}}}}}", value)
        return content

    def _send_email(self, to_email: str, subject: str, body: str):
        message = MIMEText(body, "html", "utf-8")
        message["Subject"] = subject
        message["From"] = self.settings.smtp_from_email
        message["To"] = to_email

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port) as client:
            client.sendmail(self.settings.smtp_from_email, [to_email], message.as_string())
