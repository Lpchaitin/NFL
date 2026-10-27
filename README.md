# NFL

NFL data analysis and modeling.

Data comes from [nflverse](https://github.com/nflverse) through the [`nflreadpy`](https://github.com/nflverse/nflreadpy) package: play-by-play (with EPA and win probability), player stats, rosters, schedules, snap counts, injuries, participation (personnel, formations, coverages), FTN charting (play action, RPO, blitzers), the draft, the combine and contracts.

## Setup

```bash
conda create -n nfl python=3.11 -y
conda activate nfl
pip install -r requirements.txt
```

## Get the data

```bash
python -m src.ingest                           # everything, 2016 -> current season
python -m src.ingest --start 2020 --end 2024   # a custom range
python -m src.ingest --datasets pbp schedules  # specific datasets
```

Then build the play-level table used by the notebooks (also built automatically by notebook 02):

```bash
python -m src.features
```

Files are cached as parquet in `data/raw/` and are not committed to git. Re-running skips anything already downloaded; add `--force` to refresh.

## Structure

```
nfl/
├── data/
│   ├── raw/          # downloaded nflverse data (gitignored)
│   └── processed/    # cleaned / feature tables (gitignored)
├── notebooks/        # analysis, numbered in order
├── src/
│   ├── ingest.py     # download + cache nflverse data
│   ├── features.py   # play-level table: pbp + participation + FTN charting
│   └── display.py    # shared chart style and readable tables
└── requirements.txt
```

## Roadmap

| # | Project | Key questions |
|---|---|---|
| 1 | Year-to-year offense & defense breakdown | Team level, run vs. pass, tendencies (`notebooks/01_team_season_breakdown.ipynb`) |
| 2 | Year-to-year offense & defense trends | (`notebooks/02_personnel_concepts_trends.ipynb`) Offense: personnel, run concepts, pass concepts. Defense: personnel, blitzes, coverages. What worked and what didn't? Which plays/concepts beat specific coverages/blitzes, and which coverages/blitzes beat specific plays/concepts? |
| 3 | Team and QB kryptonite | Each team's offensive and defensive weak spots by season, and each quarterback's |
| 4 | Coach & coordinator deep dives | What is Mike Macdonald's bread and butter? Kyle Shanahan's? |
| 5 | Over- and underperformers | Each season's biggest over- and underperforming teams |
