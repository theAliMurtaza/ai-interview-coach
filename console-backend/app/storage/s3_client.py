"""Private storage: stable application URLs, expiring cloud redirects at read time."""

from functools import lru_cache
from pathlib import Path, PurePosixPath

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.core.exceptions import ServiceUnavailableError, ValidationAppError


def validate_key(key: str) -> str:
    path = PurePosixPath(key)
    if (
        path.is_absolute()
        or any(p in {".", ".."} for p in key.split("/"))
        or "\\" in key
        or ":" in key
        or any(ord(char) < 32 or ord(char) == 127 for char in key)
    ):
        raise ValidationAppError("Invalid storage key")
    if not key or str(path) != key:
        raise ValidationAppError("Invalid storage key")
    return key


def local_path(key: str) -> Path:
    root = Path(settings.LOCAL_STORAGE_DIR).resolve()
    path = (root / validate_key(key)).resolve()
    if not path.is_relative_to(root):
        raise ValidationAppError("Invalid storage key")
    return path


@lru_cache
def _get_boto3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.STORAGE_ENDPOINT_URL or None,
        aws_access_key_id=settings.STORAGE_ACCESS_KEY_ID or None,
        aws_secret_access_key=settings.STORAGE_SECRET_ACCESS_KEY or None,
        region_name=settings.STORAGE_REGION,
        config=Config(connect_timeout=5, read_timeout=15, retries={"max_attempts": 2}),
    )


def upload_file(key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
    validate_key(key)
    try:
        if settings.STORAGE_BACKEND == "s3":
            _get_boto3_client().put_object(
                Bucket=settings.STORAGE_BUCKET_NAME, Key=key, Body=data, ContentType=content_type
            )
        else:
            target = local_path(key)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
    except (OSError, BotoCoreError, ClientError) as exc:
        raise ServiceUnavailableError("File storage is unavailable") from exc
    return f"{settings.API_V1_PREFIX}/files/{key}"


def generate_presigned_url(key: str, expires_in: int = 300) -> str:
    validate_key(key)
    try:
        return _get_boto3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.STORAGE_BUCKET_NAME, "Key": key},
            ExpiresIn=expires_in,
        )
    except (BotoCoreError, ClientError) as exc:
        raise ServiceUnavailableError("File storage is unavailable") from exc
