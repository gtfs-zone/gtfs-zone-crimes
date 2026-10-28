"""The feeds in data.gtfs.zone/feeds.json, cut down to what the crimes read."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

FEEDS_URL = "https://data.gtfs.zone/feeds.json"
REALTIME_ROLES = ("vehicles", "trip_updates", "alerts", "realtime")


@dataclass(frozen=True)
class CatalogFeed:
    id: str
    name: str
    subtitle: str | None
    place: str | None
    scheduled_urls: tuple[str, ...]
    # roleState.scheduled: up, down or unknown.
    scheduled_state: str | None
    # Roles only reachable with a key.
    auth: frozenset[str]
    never_up: bool
    # ISO timestamp the feed's current state began.
    since: str | None
    # Last service date from feed-catalog's content report, when it has one.
    service_end: str | None
    # trips.txt rows from feed-catalog's content report, when it has one.
    trips: int | None = None
    # First URL of each realtime role open without a key, for the viewer link.
    realtime_urls: dict[str, str] = field(default_factory=dict)

    @property
    def url(self) -> str | None:
        """The best scheduled URL, the one that is downloaded and judged."""
        return self.scheduled_urls[0] if self.scheduled_urls else None

    def summary(self, trips: int | None = None) -> dict[str, Any]:
        """What crimes.json says about the feed; `trips` is its trip count."""
        out: dict[str, Any] = {"name": self.name}
        if self.subtitle:
            out["subtitle"] = self.subtitle
        if self.place:
            out["place"] = self.place
        if self.url:
            out["url"] = self.url
        if self.realtime_urls:
            out["realtime"] = self.realtime_urls
        if trips:
            out["trips"] = trips
        return out


def place_of(entry: dict[str, Any]) -> str | None:
    parts = [entry.get(key) for key in ("municipality", "subdivision", "country")]
    place = ", ".join(part for part in parts if part)
    return place or None


def parse_feed(entry: dict[str, Any]) -> CatalogFeed:
    content = entry.get("content") or {}
    urls = entry.get("urls", {})
    auth = frozenset(entry.get("auth", []))
    return CatalogFeed(
        id=entry["feedId"],
        name=entry["name"],
        subtitle=entry.get("subtitle"),
        place=place_of(entry),
        scheduled_urls=tuple(urls.get("scheduled", [])),
        scheduled_state=entry.get("roleState", {}).get("scheduled"),
        auth=auth,
        never_up=bool(entry.get("neverUp")),
        since=entry.get("since"),
        service_end=content.get("serviceEnd"),
        trips=content.get("trips"),
        realtime_urls={
            role: urls[role][0]
            for role in REALTIME_ROLES
            if urls.get(role) and role not in auth
        },
    )


def parse_feeds(doc: dict[str, Any]) -> list[CatalogFeed]:
    """Every feed with a scheduled URL; realtime-only feeds are not judged."""
    feeds = (parse_feed(entry) for entry in doc["feeds"])
    return [feed for feed in feeds if feed.scheduled_urls]
