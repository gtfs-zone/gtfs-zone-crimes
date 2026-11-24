"""Dagster entrypoint: one asset judging every feed daily, after feed-catalog's
09:00 UTC catalog run."""

import os
from importlib.metadata import version

import httpx
from dagster import (
    AssetExecutionContext,
    DefaultScheduleStatus,
    Definitions,
    MaterializeResult,
    MetadataValue,
    ScheduleDefinition,
    asset,
    define_asset_job,
)

from gtfs_zone_crimes.catalog import FEEDS_URL
from gtfs_zone_crimes.fetch import USER_AGENT
from gtfs_zone_crimes.pipeline.bucket import Bucket, BucketSettings
from gtfs_zone_crimes.pipeline.heartbeat import push_heartbeat
from gtfs_zone_crimes.session import judge_session
from gtfs_zone_crimes.settings import Settings

VERSION = version("gtfs-zone-crimes")
CRIMES_KEY = "crimes.json"
# Per-URL validators, hashes and cached verdicts; not linked from the site.
RECORDS_KEY = "state/records.json"


@asset
def crimes(context: AssetExecutionContext) -> MaterializeResult:
    """Judge every feed in feeds.json and publish crimes.json."""
    bucket = Bucket(BucketSettings.from_env())
    zips_settings = BucketSettings.zips_from_env()
    feeds_doc = (
        httpx.get(FEEDS_URL, headers={"User-Agent": USER_AGENT}, timeout=120)
        .raise_for_status()
        .json()
    )
    doc, records, counts = judge_session(
        feeds_doc,
        bucket.get_json(CRIMES_KEY),
        bucket.get_json(RECORDS_KEY),
        Settings.from_env(),
        VERSION,
        zips=Bucket(zips_settings) if zips_settings else None,
    )
    bucket.put_json(RECORDS_KEY, records, public=False)
    bucket.put_json(CRIMES_KEY, doc)
    context.log.info("downloads: %s", counts)
    push_heartbeat()
    return MaterializeResult(
        metadata={
            "feeds": doc["feedCount"],
            "convictions": len(doc["convictions"]),
            "pardons": len(doc["pardons"]),
            "downloads": MetadataValue.json(counts),
        }
    )


# The Dagster instance runs one `gtfs.zone/memory: heavy` run at a time, so this
# never overlaps a timetable-sites shard on the node.
crimes_job = define_asset_job(
    "crimes_job", selection=[crimes], tags={"gtfs.zone/memory": "heavy"}
)

daily = ScheduleDefinition(
    job=crimes_job,
    cron_schedule=os.environ.get("CRIMES_SCHEDULE", "0 14 * * *"),
    execution_timezone="UTC",
    default_status=DefaultScheduleStatus.RUNNING,
)

defs = Definitions(assets=[crimes], jobs=[crimes_job], schedules=[daily])
