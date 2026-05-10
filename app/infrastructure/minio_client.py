import boto3
from botocore.config import Config

from app.infrastructure.config import Settings


class MinioClient:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint,
            aws_access_key_id=settings.s3_access_key,
            aws_secret_access_key=settings.s3_secret_key,
            config=Config(signature_version="s3v4", s3={"addressing_style": "path"}),
            region_name="us-east-1",
        )

    def list_excel_keys(self) -> list[str]:
        keys: list[str] = []
        continuation_token = None

        while True:
            kwargs = {
                "Bucket": self.settings.s3_bucket,
                "Prefix": self.settings.s3_leads_prefix,
                "MaxKeys": 1000,
            }
            if continuation_token:
                kwargs["ContinuationToken"] = continuation_token

            response = self.client.list_objects_v2(**kwargs)
            for item in response.get("Contents", []):
                key = item.get("Key", "")
                if key.lower().endswith(".xlsx") and not key.endswith("/"):
                    keys.append(key)

            if not response.get("IsTruncated"):
                break
            continuation_token = response.get("NextContinuationToken")

        return keys

    def read_object_bytes(self, key: str) -> bytes:
        return self.client.get_object(Bucket=self.settings.s3_bucket, Key=key)["Body"].read()
