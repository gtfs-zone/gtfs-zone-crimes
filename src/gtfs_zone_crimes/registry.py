"""Every crime, in the order the gallery lists them."""

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
    expired,
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

CRIMES: list[Crime] = [
    supersonic.CRIME,
    api_key.CRIME,
    beauty_queen.CRIME,
    deja_vu.CRIME,
    grand_central_everywhere.CRIME,
    russian_doll.CRIME,
    zip_in_name_only.CRIME,
    data_only.CRIME,
    groundhog_day.CRIME,
    every_day_is_special.CRIME,
    time_travel.CRIME,
    invisible_ink.CRIME,
    null_island.CRIME,
    shouting.CRIME,
    eternal_service.CRIME,
    disguised_as_html.CRIME,
    expired.CRIME,
    dead_link.CRIME,
]
