"""Build a play-level table: play-by-play + participation + FTN charting, with readable groupings.

    from src.features import build_play_table
    plays = build_play_table()            # reads data/raw, returns a polars DataFrame
    python -m src.features                # builds and saves data/processed/plays_enriched.parquet

One row per regular-season dropback or designed run with a valid EPA. Joins:
  * participation (2016-2025): personnel, formation, box count, pass rushers, coverage, targeted route
  * FTN charting (2022+):      play action, RPO, screen, motion, blitzers
Columns from a source are null for seasons that source doesn't cover.
"""
from __future__ import annotations

from pathlib import Path

import polars as pl

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"

PBP_COLS = [
    "season", "season_type", "week", "game_id", "play_id", "posteam", "defteam",
    "down", "ydstogo", "yardline_100", "qtr", "half_seconds_remaining", "wp", "score_differential",
    "pass", "rush", "qb_scramble", "sack", "epa", "success", "yards_gained", "air_yards",
    "shotgun", "no_huddle", "xpass", "run_location", "run_gap",
]

COVERAGE_LABELS = {
    "COVER_0": "Cover 0", "COVER_1": "Cover 1", "2_MAN": "2-Man", "COVER_2": "Cover 2",
    "COVER_3": "Cover 3", "COVER_4": "Cover 4 (Quarters)", "COVER_6": "Cover 6",
    "COVER_9": "Cover 9", "COMBO": "Combo", "BLOWN": "Blown", "PREVENT": "Prevent",
}


def _read_seasons(folder: str, columns: list[str] | None = None) -> pl.DataFrame:
    files = sorted((RAW / folder).glob(f"{folder}_*.parquet"))
    if not files:
        raise FileNotFoundError(f"No files in {RAW / folder}. Run: python -m src.ingest --datasets {folder}")
    frames = []
    for f in files:
        df = pl.read_parquet(f)
        frames.append(df.select([c for c in columns if c in df.columns]) if columns else df)
    return pl.concat(frames, how="diagonal_relaxed")


def _count(col: str, *positions: str) -> pl.Expr:
    """Sum the counts for the given position codes in a personnel string like '1 RB, 2 TE, 2 WR'."""
    exprs = [pl.col(col).str.extract(rf"(\d+) {p}\b", 1).cast(pl.Int32).fill_null(0) for p in positions]
    return pl.sum_horizontal(exprs)


def _blank_to_null(col: str) -> pl.Expr:
    return pl.when(pl.col(col).str.strip_chars() == "").then(None).otherwise(pl.col(col)).alias(col)


def load_participation() -> pl.DataFrame:
    part = _read_seasons("participation", [
        "nflverse_game_id", "play_id", "offense_formation", "offense_personnel", "defense_personnel",
        "defenders_in_box", "number_of_pass_rushers", "was_pressure", "time_to_throw", "route",
        "defense_man_zone_type", "defense_coverage_type",
    ]).rename({"nflverse_game_id": "game_id"})

    part = part.with_columns(
        pl.col("play_id").cast(pl.Int64),
        _blank_to_null("route"), _blank_to_null("defense_man_zone_type"), _blank_to_null("defense_coverage_type"),
        # offensive personnel: RB (incl. FB), TE, WR, and offensive linemen (old format lists OL only when 6+)
        off_rb=_count("offense_personnel", "RB", "FB"),
        off_te=_count("offense_personnel", "TE"),
        off_wr=_count("offense_personnel", "WR"),
        off_ol=_count("offense_personnel", "OL", "C", "G", "T"),
        # defensive personnel: defensive backs decide base / nickel / dime
        def_db=_count("defense_personnel", "DB", "CB", "S", "FS", "SS"),
        def_dl=_count("defense_personnel", "DL", "DE", "DT", "NT"),
        def_lb=_count("defense_personnel", "LB", "ILB", "OLB", "MLB"),
    )
    has_off = pl.col("offense_personnel").is_not_null()
    has_def = pl.col("defense_personnel").is_not_null()
    return part.with_columns(
        personnel=pl.when(has_off).then(pl.format("{}{}", pl.col("off_rb"), pl.col("off_te"))),
        extra_ol=pl.when(has_off).then(pl.col("off_ol") >= 6),
        def_package=pl.when(~has_def).then(None)
            .when(pl.col("def_db") <= 3).then(pl.lit("Heavy (3 or fewer DBs)"))
            .when(pl.col("def_db") == 4).then(pl.lit("Base (4 DBs)"))
            .when(pl.col("def_db") == 5).then(pl.lit("Nickel (5 DBs)"))
            .otherwise(pl.lit("Dime+ (6+ DBs)")),
        man_zone=pl.col("defense_man_zone_type").replace({"MAN_COVERAGE": "Man", "ZONE_COVERAGE": "Zone"}),
        coverage=pl.col("defense_coverage_type").replace(COVERAGE_LABELS),
        # 0 means "not charted / not applicable" for these
        box=pl.when(pl.col("defenders_in_box") > 0).then(pl.col("defenders_in_box")),
        rushers=pl.when(pl.col("number_of_pass_rushers") > 0).then(pl.col("number_of_pass_rushers")),
    ).drop("defense_man_zone_type", "defense_coverage_type", "defenders_in_box", "number_of_pass_rushers")


def load_ftn() -> pl.DataFrame:
    return (
        _read_seasons("ftn_charting", [
            "nflverse_game_id", "nflverse_play_id", "is_play_action", "is_rpo", "is_screen_pass",
            "is_motion", "n_blitzers", "n_pass_rushers", "qb_location", "is_trick_play",
        ])
        .rename({"nflverse_game_id": "game_id", "nflverse_play_id": "play_id",
                 "n_pass_rushers": "ftn_pass_rushers"})
        .with_columns(pl.col("play_id").cast(pl.Int64))
        .unique(["game_id", "play_id"], keep="first")
    )


def build_play_table() -> pl.DataFrame:
    pbp = _read_seasons("pbp", PBP_COLS)
    plays = pbp.filter(
        (pl.col("season_type") == "REG")
        & ((pl.col("pass") == 1) | (pl.col("rush") == 1))
        & pl.col("epa").is_not_null()
        & pl.col("posteam").is_not_null()
    ).with_columns(pl.col("play_id").cast(pl.Int64))
    plays = (
        plays.join(load_participation(), on=["game_id", "play_id"], how="left")
             .join(load_ftn(), on=["game_id", "play_id"], how="left")
    )

    is_pass, is_rush = pl.col("pass") == 1, pl.col("rush") == 1
    formation = pl.col("offense_formation")
    return plays.with_columns(
        play_kind=pl.when(is_pass).then(pl.lit("Dropback")).otherwise(pl.lit("Designed run")),
        neutral=(pl.col("down") <= 2) & pl.col("wp").is_between(0.2, 0.8) & (pl.col("half_seconds_remaining") > 120),
        explosive=(is_pass & (pl.col("yards_gained") >= 20)) | (is_rush & (pl.col("yards_gained") >= 10)),
        # QB alignment, harmonized: 2016-22 used SINGLEBACK / I_FORM / EMPTY ..., 2023+ uses UNDER CENTER
        alignment=pl.when(formation == "PISTOL").then(pl.lit("Pistol"))
            .when(formation.is_in(["SHOTGUN", "EMPTY"])).then(pl.lit("Shotgun"))
            .when(formation.is_in(["UNDER CENTER", "SINGLEBACK", "I_FORM", "JUMBO"])).then(pl.lit("Under center"))
            .when(formation == "WILDCAT").then(pl.lit("Wildcat"))
            .when(pl.col("shotgun") == 1).then(pl.lit("Shotgun"))
            .otherwise(pl.lit("Under center")),
        personnel_group=pl.when(pl.col("personnel").is_in(["11", "12", "21", "13", "10", "22"]))
            .then(pl.col("personnel")).when(pl.col("personnel").is_not_null()).then(pl.lit("Other")),
        box_group=pl.when(pl.col("box") <= 6).then(pl.lit("Light (6 or fewer)"))
            .when(pl.col("box") == 7).then(pl.lit("Neutral (7)"))
            .when(pl.col("box") >= 8).then(pl.lit("Stacked (8+)")),
        rush_group=pl.when(~is_pass | pl.col("rushers").is_null()).then(None)
            .when(pl.col("rushers") <= 3).then(pl.lit("3 or fewer (drop 8)"))
            .when(pl.col("rushers") == 4).then(pl.lit("4 (standard)"))
            .when(pl.col("rushers") == 5).then(pl.lit("5 (blitz)"))
            .otherwise(pl.lit("6+ (heavy blitz)")),
        blitz=pl.when(is_pass & pl.col("rushers").is_not_null()).then(pl.col("rushers") >= 5),
        depth=pl.when(~is_pass | pl.col("air_yards").is_null()).then(None)
            .when(pl.col("air_yards") < 0).then(pl.lit("Behind line"))
            .when(pl.col("air_yards") < 10).then(pl.lit("Short (0-9)"))
            .when(pl.col("air_yards") < 20).then(pl.lit("Intermediate (10-19)"))
            .otherwise(pl.lit("Deep (20+)")),
        run_direction=pl.when(~is_rush | pl.col("run_location").is_null()).then(None)
            .when(pl.col("run_location") == "middle").then(pl.lit("Middle"))
            .otherwise(pl.format("{} {}", pl.col("run_location").str.to_titlecase(), pl.col("run_gap").fill_null("?"))),
        run_lane=pl.when(~is_rush | pl.col("run_location").is_null()).then(None)
            .when((pl.col("run_location") == "middle") | (pl.col("run_gap") == "guard")).then(pl.lit("Inside"))
            .otherwise(pl.lit("Outside")),
    )


if __name__ == "__main__":
    PROCESSED.mkdir(parents=True, exist_ok=True)
    table = build_play_table()
    out = PROCESSED / "plays_enriched.parquet"
    table.write_parquet(out)
    print(f"Saved {table.height:,} plays x {table.width} columns -> {out}")
