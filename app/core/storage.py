import asyncio
import io
import uuid

import boto3
from botocore.exceptions import ClientError
from PIL import Image

from app.settings import settings


def _s3_client():
    return boto3.client(
        "s3",
        endpoint_url=settings.S3_ENDPOINT_URL or None,
        aws_access_key_id=settings.S3_ACCESS_KEY,
        aws_secret_access_key=settings.S3_SECRET_KEY,
    )


def _sync_upload(data: bytes, key: str, content_type: str) -> str:
    s3 = _s3_client()
    s3.put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=data,
        ContentType=content_type,
    )
    base = settings.S3_PUBLIC_URL.rstrip("/")
    return f"{base}/{key}"


def _sync_delete(key: str) -> None:
    s3 = _s3_client()
    try:
        s3.delete_object(Bucket=settings.S3_BUCKET_NAME, Key=key)
    except ClientError:
        pass


async def upload_image(data: bytes, folder: str = "products") -> tuple[str, str]:
    name = uuid.uuid4().hex
    img = Image.open(io.BytesIO(data)).convert("RGB")

    img.thumbnail((1200, 1200), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=85)
    url = await asyncio.to_thread(
        _sync_upload, buf.getvalue(), f"{folder}/{name}.webp", "image/webp"
    )

    img.thumbnail((400, 400), Image.LANCZOS)
    tbuf = io.BytesIO()
    img.save(tbuf, "WEBP", quality=75)
    thumb_url = await asyncio.to_thread(
        _sync_upload, tbuf.getvalue(), f"{folder}/thumbs/{name}.webp", "image/webp"
    )

    return url, thumb_url


async def delete_image_by_url(url: str) -> None:
    if not settings.S3_PUBLIC_URL or not url.startswith(settings.S3_PUBLIC_URL):
        return
    base = settings.S3_PUBLIC_URL.rstrip("/") + "/"
    key = url[len(base):]
    await asyncio.to_thread(_sync_delete, key)
