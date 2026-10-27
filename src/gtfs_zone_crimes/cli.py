"""`crimes judge`: one session against a local state directory, for development.
Reads and writes crimes.json and records.json there."""

from __future__ import annotations

import argparse
import json
import logging
from importlib.metadata import version
from pathlib import Path

import httpx

from gtfs_zone_crimes.catalog import FEEDS_URL
from gtfs_zone_crimes.fetch import USER_AGENT
from gtfs_zone_crimes.session import judge_session
from gtfs_zone_crimes.settings import Settings


def read(path: Path) -> dict | None:
    return json.loads(path.read_text()) if path.exists() else None


def main() -> None:
    parser = argparse.ArgumentParser(prog="crimes")
    commands = parser.add_subparsers(dest="command", required=True)
    judge = commands.add_parser("judge", help="judge feeds into a state directory")
    judge.add_argument("--out", type=Path, default=Path("web/dev-data"))
    judge.add_argument(
        "--feeds-json", help="a local feeds.json instead of the published one"
    )
    args = parser.parse_args()
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )

    if args.feeds_json:
        feeds_doc = json.loads(Path(args.feeds_json).read_text())
    else:
        feeds_doc = (
            httpx.get(FEEDS_URL, headers={"User-Agent": USER_AGENT}, timeout=120)
            .raise_for_status()
            .json()
        )
    args.out.mkdir(parents=True, exist_ok=True)
    crimes, records, counts = judge_session(
        feeds_doc,
        read(args.out / "crimes.json"),
        read(args.out / "records.json"),
        Settings.from_env(),
        version("gtfs-zone-crimes"),
    )
    (args.out / "crimes.json").write_text(json.dumps(crimes, ensure_ascii=False))
    (args.out / "records.json").write_text(json.dumps(records, ensure_ascii=False))
    print(json.dumps(counts, indent=1))
