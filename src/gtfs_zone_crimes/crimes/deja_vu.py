"""Deja vu: the same shape over and over under different shape_ids. Shapes that
start and end within the same ~100 m, pass the same point halfway along to
within ~1 km, and run the same length to within a few percent are copies, where
one shape could serve every trip. Points are compared rounded, so copies either
side of a rounding boundary count as different: the count only ever comes out
low. Plenty of feeds have a few copies among their pattern variants; the crime
is shipping thousands."""

import polars as pl

from gtfs_zone_crimes.crime import ACQUITTED, Crime, Scope, Verdict
from gtfs_zone_crimes.parse import SHAPES_SAMPLE_BYTES, Gtfs, haversine_km

# Copies in the whole of shapes.txt, scaled up from the sample when it was cut.
MIN_COPIES = 2000
MIN_SHARE = 0.15
# Decimal places endpoints and the halfway point are compared at: 3 is about
# 100 m, 2 about 1 km.
END_PLACES = 3
MID_PLACES = 2
# Lengths chained within this fraction (plus 50 m) are the same length.
LENGTH_TOLERANCE = 0.05
SHOWN_IDS = 3


def judge(gtfs: Gtfs) -> Verdict | None:
    entry = gtfs.facts.member("shapes.txt")
    if entry is None:
        return ACQUITTED
    points = gtfs.shape_points()
    if points is None:
        return ACQUITTED
    lat, lon = pl.col("lat"), pl.col("lon")
    # Hops are taken in file order, as in beauty_queen: a point continues the
    # shape of the row before it when its sequence is higher.
    same = (pl.col("shape_id").shift(1) == pl.col("shape_id")) & (
        pl.col("seq").shift(1) < pl.col("seq")
    )
    ordered = pl.col("km").sort_by("seq")
    halfway = ordered.cum_sum() >= ordered.sum() / 2
    shapes = gtfs.collect(
        points.with_columns(
            pl.col("shape_id").cast(pl.Categorical),
            km=pl.when(same)
            .then(haversine_km(lat.shift(1), lon.shift(1), lat, lon))
            .otherwise(0.0),
        )
        .group_by("shape_id")
        .agg(
            lat0=lat.sort_by("seq").first().round(END_PLACES),
            lon0=lon.sort_by("seq").first().round(END_PLACES),
            lat1=lat.sort_by("seq").last().round(END_PLACES),
            lon1=lon.sort_by("seq").last().round(END_PLACES),
            latm=lat.sort_by("seq").filter(halfway).first().round(MID_PLACES),
            lonm=lon.sort_by("seq").filter(halfway).first().round(MID_PLACES),
            km=pl.col("km").sum(),
        )
    )
    total = shapes.height
    if not total:
        return ACQUITTED
    route = ["lat0", "lon0", "lat1", "lon1", "latm", "lonm"]
    # Within one route, sorted by length, a shape starts a new group when it is
    # longer than the one before by more than the tolerance.
    new_route = pl.any_horizontal(
        pl.col(c).ne_missing(pl.col(c).shift(1)) for c in route
    )
    longer = pl.col("km") > pl.col("km").shift(1) * (1 + LENGTH_TOLERANCE) + 0.05
    groups = (
        shapes.sort([*route, "km"])
        .with_columns(group=(new_route | longer.fill_null(True)).cum_sum())
        .group_by("group")
        .agg(
            copies=pl.len(),
            ids=pl.col("shape_id").cast(pl.String).sort().head(SHOWN_IDS),
            km=pl.col("km").mean(),
        )
        .sort("copies", "km", descending=True)
    )
    redundant = total - groups.height
    sample = gtfs.extract("shapes", SHAPES_SAMPLE_BYTES)
    assert sample is not None
    scale = entry.size / max(sample.stat().st_size, 1)
    share = redundant / total
    copies = round(redundant * scale)
    if copies < MIN_COPIES or share < MIN_SHARE:
        return ACQUITTED
    about = "About " if scale > 1.01 else ""
    details = [
        f"{row['copies']:,} shapes like {', '.join(row['ids'])} ({row['km']:,.1f} km)"
        for row in groups.filter(pl.col("copies") > 1).head(10).iter_rows(named=True)
    ]
    return Verdict(
        guilty=True,
        summary=(
            f"{about}{copies:,} of {round(total * scale):,} shapes ({share:.0%}) "
            "repeat another one"
        ),
        metric=copies,
        details=details,
    )


CRIME = Crime(slug="deja-vu", scope=Scope.CONTENT, judge=judge)
