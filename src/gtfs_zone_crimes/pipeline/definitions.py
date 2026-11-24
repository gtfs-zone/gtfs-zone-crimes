"""Dagster entrypoint: one asset judging every feed after each feed-catalog
`published_artifacts` materialization."""

from importlib.metadata import version

import httpx
from dagster import (
    AssetExecutionContext,
    AssetKey,
    AutomationCondition,
    AutomationConditionSensorDefinition,
    DefaultSensorStatus,
    Definitions,
    MaterializeResult,
    MetadataValue,
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
# feed-catalog's asset, in another code location of the same instance: it
# publishes feeds.json and the gtfs-zips index the crimes read.
PUBLISHED_ARTIFACTS = AssetKey("published_artifacts")


@asset(
    deps=[PUBLISHED_ARTIFACTS],
    automation_condition=AutomationCondition.eager(),
)
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
HEAVY = {"gtfs.zone/memory": "heavy"}

crimes_job = define_asset_job("crimes_job", selection=[crimes], tags=HEAVY)

# Requests a crimes run after each new published_artifacts materialization.
after_catalog = AutomationConditionSensorDefinition(
    "after_catalog",
    target=[crimes],
    run_tags=HEAVY,
    default_status=DefaultSensorStatus.RUNNING,
)

defs = Definitions(assets=[crimes], jobs=[crimes_job], sensors=[after_catalog])
