# NFL

NFL data analysis and modeling.

Data comes from [nflverse](https://github.com/nflverse) through the [`nflreadpy`](https://github.com/nflverse/nflreadpy) package: play-by-play (with EPA and win probability), player stats, rosters, schedules, snap counts, injuries, the draft, the combine and contracts.

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

Files are cached as parquet in `data/raw/` and are not committed to git. Re-running skips anything already downloaded; add `--force` to refresh.

## Structure

```
nfl/
├── data/
│   ├── raw/          # downloaded nflverse data (gitignored)
│   └── processed/    # cleaned / feature tables (gitignored)
├── notebooks/        # analysis, numbered in order
├── src/
│   └── ingest.py     # download + cache nflverse data
└── requirements.txt
```
