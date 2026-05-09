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
    s3_endpoint: str
    s3_access_key: str
    s3_secret_key: str
    s3_bucket: str
    s3_leads_prefix: str

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
            s3_endpoint=os.getenv("S3_ENDPOINT", "http://minio:9000"),
            s3_access_key=os.getenv("S3_ACCESS_KEY", os.getenv("MINIO_ROOT_USER", "")),
            s3_secret_key=os.getenv("S3_SECRET_KEY", os.getenv("MINIO_ROOT_PASSWORD", "")),
            s3_bucket=os.getenv("S3_BUCKET", "lingua-sync"),
            s3_leads_prefix=os.getenv("S3_LEADS_PREFIX", "leads/"),
        )
