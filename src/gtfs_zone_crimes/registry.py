"""Every crime, in the order the site lists them."""

from gtfs_zone_crimes.crime import Crime
from gtfs_zone_crimes.crimes import (
    api_key,
    beauty_queen,
    data_only,
    dead_link,
    deja_vu,
    disguised_as_html,
    eternal_service,
    every_day_is_special,
    grand_central_everywhere,
    groundhog_day,
    invisible_ink,
    null_island,
    russian_doll,
    shouting,
    supersonic,
    time_travel,
    zip_in_name_only,
)

# Ranked by hand, most notable first: clearly broken data at the top,
# opinions and low-impact crimes at the bottom. The site keeps this order,
# so place a new crime by notability rather than appending it.
CRIMES: list[Crime] = [
    time_travel.CRIME,
    supersonic.CRIME,
    api_key.CRIME,
    null_island.CRIME,
    deja_vu.CRIME,
    invisible_ink.CRIME,
    russian_doll.CRIME,
    grand_central_everywhere.CRIME,
    eternal_service.CRIME,
    every_day_is_special.CRIME,
    beauty_queen.CRIME,
    groundhog_day.CRIME,
    zip_in_name_only.CRIME,
    disguised_as_html.CRIME,
    data_only.CRIME,
    shouting.CRIME,
    dead_link.CRIME,
]
