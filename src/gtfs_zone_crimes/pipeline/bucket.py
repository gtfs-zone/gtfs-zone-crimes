"""The crimes bucket over the S3 API."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

# crimes.json refreshes daily, so browsers and proxies may keep it only briefly.
CACHE_CONTROL = "public, max-age=600"


@dataclass(frozen=True)
class BucketSettings:
    endpoint: str
    bucket: str
    access_key: str
    secret_key: str
    region: str

    @classmethod
    def from_env(cls) -> BucketSettings:
        return cls(
            endpoint=os.environ["S3_ENDPOINT"],
            bucket=os.environ.get("S3_BUCKET", "crimes.gtfs.zone"),
            access_key=os.environ["S3_ACCESS_KEY"],
            secret_key=os.environ["S3_SECRET_KEY"],
            region=os.environ.get("S3_REGION", "garage"),
        )


class Bucket:
    def __init__(self, settings: BucketSettings) -> None:
        self.name = settings.bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=settings.endpoint,
            aws_access_key_id=settings.access_key,
            aws_secret_access_key=settings.secret_key,
            region_name=settings.region,
            # Garage serves every bucket from one host, so the bucket goes in
            # the path.
            config=Config(s3={"addressing_style": "path"}, retries={"max_attempts": 3}),
        )

    def get_json(self, key: str) -> dict[str, Any] | None:
        """The object parsed as JSON, or None when there is no such key."""
        try:
            response = self._client.get_object(Bucket=self.name, Key=key)
        except ClientError as exc:
            if exc.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                return None
            raise
        with response["Body"] as stream:
            return json.loads(stream.read())

    def put_json(self, key: str, doc: dict[str, Any], public: bool = True) -> None:
        self._client.put_object(
            Bucket=self.name,
            Key=key,
            Body=json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode(),
            ContentType="application/json",
            CacheControl=CACHE_CONTROL if public else "no-store",
        )
