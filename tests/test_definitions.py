import dagster as dg

from gtfs_zone_crimes.pipeline import definitions

CRIMES = dg.AssetKey("crimes")


def test_crimes_run_once_after_published_artifacts() -> None:
    instance = dg.DagsterInstance.ephemeral()
    instance.report_runless_asset_event(dg.AssetMaterialization(CRIMES))
    result = dg.evaluate_automation_conditions(definitions.defs, instance)
    assert result.total_requested == 0

    instance.report_runless_asset_event(
        dg.AssetMaterialization(definitions.PUBLISHED_ARTIFACTS)
    )
    result = dg.evaluate_automation_conditions(
        definitions.defs, instance, cursor=result.cursor
    )
    assert result.get_num_requested(CRIMES) == 1

    result = dg.evaluate_automation_conditions(
        definitions.defs, instance, cursor=result.cursor
    )
    assert result.total_requested == 0


def test_after_catalog_runs_are_heavy() -> None:
    assert definitions.after_catalog.run_tags == {"gtfs.zone/memory": "heavy"}
    assert not list(definitions.defs.schedules or [])
