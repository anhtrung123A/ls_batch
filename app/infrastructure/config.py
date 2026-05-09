import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    db_host: str
    db_port: int
    db_name: str
    db_user: str
    db_password: str
    smtp_host: str
    smtp_port: int
    smtp_from_email: str
    smtp_from_name: str
    log_level: str

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_host=os.getenv("DB_HOST", "localhost"),
            db_port=int(os.getenv("DB_PORT", "3306")),
            db_name=os.getenv("DB_NAME", "lingua_sync"),
            db_user=os.getenv("DB_USER", "root"),
            db_password=os.getenv("DB_PASSWORD", ""),
            smtp_host=os.getenv("SMTP_HOST", ""),
            smtp_port=int(os.getenv("SMTP_PORT", "25")),
            smtp_from_email=os.getenv("SMTP_FROM_EMAIL", ""),
            smtp_from_name=os.getenv("SMTP_FROM_NAME", ""),
            log_level=os.getenv("LOG_LEVEL", "INFO"),
        )
