"""Ingest CLI: pull public sources into the bronze layer, then build dbt.

    grid-ingest all --start 2025-07-01 --end 2026-11-09
    grid-ingest eia930 --start 2026-07-01 --ba PJM
    grid-ingest nrc --start 2026-10-10
    grid-ingest weather --start 2026-10-10
"""
from __future__ import annotations

import argparse
import datetime as dt
from pathlib import Path

from .config import BRONZE_DIR, DEFAULT_BAS, RAW_DIR
from .sources import eia930, nrc, weather


def _date(s: str) -> dt.date:
    return dt.date.fromisoformat(s)


def main() -> None:
    parser = argparse.ArgumentParser(prog="grid-ingest", description=__doc__)
    parser.add_argument("source", choices=["eia930", "nrc", "weather", "all"])
    parser.add_argument("--start", type=_date, required=True)
    parser.add_argument("--end", type=_date, default=dt.date.today())
    parser.add_argument("--ba", default=",".join(DEFAULT_BAS),
                        help="comma-separated balancing authorities")
    parser.add_argument("--bronze-dir", type=Path, default=BRONZE_DIR)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    args = parser.parse_args()

    bas = tuple(b.strip().upper() for b in args.ba.split(",") if b.strip())
    if args.source in ("eia930", "all"):
        written = eia930.ingest(args.start, args.end, bas,
                                args.raw_dir, args.bronze_dir)
        print(f"eia930: {len(written)} parquet file(s)")
    if args.source in ("nrc", "all"):
        written = nrc.ingest(args.start, args.end, args.bronze_dir)
        print(f"nrc: {len(written)} parquet file(s)")
    if args.source in ("weather", "all"):
        dest = weather.ingest(args.start, args.end, dest_dir=args.bronze_dir)
        print(f"weather: {dest}")


if __name__ == "__main__":
    main()
