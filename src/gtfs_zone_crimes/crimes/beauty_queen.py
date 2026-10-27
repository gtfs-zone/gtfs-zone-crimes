"""Beauty queen: shapes.txt drawn to the millimetre. Shape points closer than a
couple of metres apart, and shapes.txt the biggest file in the feed."""

import polars as pl

from gtfs_zone_crimes.crime import ACQUITTED, Crime, Scope, Verdict
from gtfs_zone_crimes.parse import SHAPES_SAMPLE_BYTES, Gtfs, haversine_km

MAX_MEDIAN_M = 2.0


def judge(gtfs: Gtfs) -> Verdict | None:
    entry = gtfs.facts.member("shapes.txt")
    if entry is None:
        return ACQUITTED
    shapes = gtfs.shape_points()
    if shapes is None:
        return ACQUITTED
    # Points are taken in file order, which producers write shape by shape: a
    # point counts when it follows one of the same shape with a lower
    # sequence. Sorting a multi-gigabyte shapes.txt would cost more memory
    # than the rest of the feed, and a sample cannot be sorted anyway.
    lat, lon = pl.col("lat"), pl.col("lon")
    same = (pl.col("shape").shift(1) == pl.col("shape")) & (
        pl.col("seq").shift(1) < pl.col("seq")
    )
    stats = gtfs.collect(
        shapes.select(shape=pl.col("shape_id").hash(), lat="lat", lon="lon", seq="seq")
        .select(
            m=pl.when(same).then(
                haversine_km(lat.shift(1), lon.shift(1), lat, lon) * 1000
            ),
            points=pl.len(),
        )
        .select(
            points=pl.col("points").first(),
            median_m=pl.col("m").median(),
            total_km=pl.col("m").sum() / 1000,
        )
    ).row(0, named=True)
    if not stats["points"] or stats["median_m"] is None:
        return ACQUITTED
    largest = max(gtfs.facts.files, key=lambda e: e.size)
    if stats["median_m"] >= MAX_MEDIAN_M or largest.name != entry.name:
        return ACQUITTED
    share = entry.size / max(gtfs.facts.uncompressed_bytes(), 1)
    per_km = stats["points"] / max(stats["total_km"], 0.001)
    sample = gtfs.extract("shapes", SHAPES_SAMPLE_BYTES)
    assert sample is not None
    # Scaled up from the sample when shapes.txt was cut.
    points = round(stats["points"] * entry.size / max(sample.stat().st_size, 1))
    return Verdict(
        guilty=True,
        summary=(
            f"{stats['median_m'] * 100:,.0f} cm between shape points "
            f"({per_km:,.0f} per km); shapes.txt is {share:.0%} of the feed"
        ),
        metric=round(per_km, 1),
        details=[
            f"About {points:,} shape points",
            f"shapes.txt: {entry.size / 1e6:,.1f} MB uncompressed",
        ],
    )


CRIME = Crime(slug="beauty-queen", scope=Scope.CONTENT, judge=judge)
