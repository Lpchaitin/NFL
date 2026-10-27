"""Download NFL data from nflverse (via nflreadpy) and cache it as parquet.

Usage:
    python -m src.ingest                          # all datasets, 2016 -> current season
    python -m src.ingest --start 2020 --end 2024  # custom season range
    python -m src.ingest --datasets pbp schedules # only some datasets
    python -m src.ingest --force                  # re-download even if cached
"""
from __future__ import annotations

import argparse
from pathlib import Path

import nflreadpy as nfl

RAW_DIR = Path(__file__).resolve().parents[1] / "data" / "raw"

# Datasets pulled one season at a time -> data/raw/<name>/<name>_<season>.parquet
SEASONAL = {
    "pbp": nfl.load_pbp,
    "player_stats": nfl.load_player_stats,
    "rosters": nfl.load_rosters,
    "schedules": nfl.load_schedules,
    "snap_counts": nfl.load_snap_counts,
    "injuries": nfl.load_injuries,
    "participation": nfl.load_participation,  # personnel, formation, coverage, pass rushers, routes
    "ftn_charting": nfl.load_ftn_charting,    # play action, RPO, screens, motion, blitzers
}

# Seasons each source actually publishes (None = no limit). Out-of-range seasons are skipped.
SEASON_LIMITS = {
    "participation": (2016, 2025),
    "ftn_charting": (2022, None),
}

# Datasets pulled as one full table -> data/raw/<name>.parquet
FULL = {
    "draft_picks": nfl.load_draft_picks,
    "combine": nfl.load_combine,
    "contracts": nfl.load_contracts,
    "teams": nfl.load_teams,
    "players": nfl.load_players,
}


def pull_seasonal(name: str, seasons: list[int], force: bool) -> None:
    out_dir = RAW_DIR / name
    out_dir.mkdir(parents=True, exist_ok=True)
    lo, hi = SEASON_LIMITS.get(name, (None, None))
    for season in seasons:
        if (lo and season < lo) or (hi and season > hi):
            print(f"  n/a   {name} {season} (not published for this season)")
            continue
        path = out_dir / f"{name}_{season}.parquet"
        if path.exists() and not force:
            print(f"  skip  {path.name} (cached)")
            continue
        try:
            df = SEASONAL[name](season)
        except Exception as exc:  # season not published yet, network error, etc.
            print(f"  FAIL  {name} {season}: {exc}")
            continue
        df.write_parquet(path)
        print(f"  saved {path.name}  {df.height:,} rows x {df.width} cols")


def pull_full(name: str, force: bool) -> None:
    path = RAW_DIR / f"{name}.parquet"
    if path.exists() and not force:
        print(f"  skip  {path.name} (cached)")
        return
    try:
        df = FULL[name]()
    except Exception as exc:
        print(f"  FAIL  {name}: {exc}")
        return
    df.write_parquet(path)
    print(f"  saved {path.name}  {df.height:,} rows x {df.width} cols")


def main() -> None:
    all_names = list(SEASONAL) + list(FULL)
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--start", type=int, default=2016, help="first season (default 2016)")
    parser.add_argument("--end", type=int, default=nfl.get_current_season(), help="last season (default: current)")
    parser.add_argument("--datasets", nargs="+", choices=all_names, default=all_names)
    parser.add_argument("--force", action="store_true", help="re-download cached files")
    args = parser.parse_args()

    seasons = list(range(args.start, args.end + 1))
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Seasons {args.start}-{args.end} -> {RAW_DIR}")

    for name in args.datasets:
        print(f"\n[{name}]")
        if name in SEASONAL:
            pull_seasonal(name, seasons, args.force)
        else:
            pull_full(name, args.force)


if __name__ == "__main__":
    main()
