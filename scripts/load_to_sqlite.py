"""Load the synthetic raw datasets into a SQLite database."""

from __future__ import annotations

from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
DATABASE_PATH = PROJECT_ROOT / "database" / "streamsense.db"

DATASET_FILES = [
    ("subscriber_data.csv", "subscriber_data"),
    ("content_metadata.csv", "content_metadata"),
    ("viewer_activity.csv", "viewer_activity"),
]


def load_all_tables(database_path: str | Path = DATABASE_PATH) -> None:
    """Read each raw CSV file and persist it as a SQLite table."""
    engine = create_engine(f"sqlite:///{database_path}")
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)

    for filename, table_name in DATASET_FILES:
        csv_path = RAW_DATA_DIR / filename
        if not csv_path.exists():
            raise FileNotFoundError(f"Missing file for import: {csv_path}")

        frame = pd.read_csv(csv_path)
        frame.to_sql(table_name, con=engine, if_exists="replace", index=False)
        print(f"Loaded {len(frame):,} rows into {table_name}.")


if __name__ == "__main__":
    load_all_tables()
