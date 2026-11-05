"""The crimes bucket over the S3 API."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

import obstore

if TYPE_CHECKING:
    from obstore.store import ObjectStore

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


def s3_store(settings: BucketSettings) -> ObjectStore:
    from obstore.store import S3Store

    return S3Store(
        settings.bucket,
        endpoint=settings.endpoint,
        region=settings.region,
        access_key_id=settings.access_key,
        secret_access_key=settings.secret_key,
        # Garage serves every bucket from one host, so the bucket goes in the
        # path.
        virtual_hosted_style_request=False,
        client_options={
            "allow_http": settings.endpoint.startswith("http://"),
            "timeout": "120s",
        },
    )


class Bucket:
    """get_json / put_json against one bucket, or against `store`."""

    def __init__(
        self, settings: BucketSettings, store: ObjectStore | None = None
    ) -> None:
        self.name = settings.bucket
        self._store = store if store is not None else s3_store(settings)

    def get_json(self, key: str) -> dict[str, Any] | None:
        """The object parsed as JSON, or None when there is no such key."""
        try:
            return json.loads(bytes(obstore.get(self._store, key).bytes()))
        except FileNotFoundError:
            return None

    def put_json(self, key: str, doc: dict[str, Any], public: bool = True) -> None:
        obstore.put(
            self._store,
            key,
            json.dumps(doc, ensure_ascii=False, separators=(",", ":")).encode(),
            use_multipart=False,
            attributes={
                "Content-Type": "application/json",
                "Cache-Control": CACHE_CONTROL if public else "no-store",
            },
        )
