"""Generate realistic, connected synthetic data for StreamSense AI.

The data intentionally encodes plausible behavioural relationships: sustained
watching, high completion, and repeat sessions align with retention, while
frequent pausing and low completion increase churn likelihood.  It is synthetic
and suitable only for demonstration and analytics practice.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker


SEED = 42
SUBSCRIBER_COUNT = 1_000
CONTENT_COUNT = 100
SESSION_COUNT = 10_000
REFERENCE_DATE = date(2026, 8, 1)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"

PERSONAS = {
    "Binge Watcher": {
        "weight": 0.24,
        "sessions": 16,
        "completion": 82,
        "watch_minutes": 51,
        "pauses": 1.1,
        "retention": 0.78,
    },
    "Casual Viewer": {
        "weight": 0.30,
        "sessions": 8,
        "completion": 62,
        "watch_minutes": 34,
        "pauses": 1.7,
        "retention": 0.66,
    },
    "Weekend Viewer": {
        "weight": 0.18,
        "sessions": 7,
        "completion": 71,
        "watch_minutes": 42,
        "pauses": 1.4,
        "retention": 0.72,
    },
    "Documentary Fan": {
        "weight": 0.13,
        "sessions": 9,
        "completion": 76,
        "watch_minutes": 47,
        "pauses": 1.0,
        "retention": 0.75,
    },
    "At-Risk Viewer": {
        "weight": 0.15,
        "sessions": 4,
        "completion": 35,
        "watch_minutes": 19,
        "pauses": 3.8,
        "retention": 0.38,
    },
}

GENRES = ["Drama", "Comedy", "Documentary", "Thriller", "Sci-Fi", "Reality", "Animation", "Crime"]
LANGUAGES = ["English", "Hindi", "Spanish", "Korean", "French"]
PLANS = ["Basic", "Standard", "Premium"]
DEVICES = ["Smart TV", "Mobile", "Laptop", "Tablet"]


def clipped_normal(rng: np.random.Generator, mean: float, standard_deviation: float, low: float, high: float) -> float:
    """Return a normally distributed number clipped to a business-valid range."""
    return float(np.clip(rng.normal(mean, standard_deviation), low, high))


def generate_content(rng: np.random.Generator, fake: Faker) -> pd.DataFrame:
    """Create a catalog with mixed genres, formats, and content quality signals."""
    rows: list[dict[str, object]] = []
    genre_weights = [0.22, 0.17, 0.12, 0.13, 0.11, 0.10, 0.07, 0.08]

    for index in range(1, CONTENT_COUNT + 1):
        genre = rng.choice(GENRES, p=genre_weights)
        content_type = "Movie" if rng.random() < 0.22 else "Series"
        release_year = int(rng.integers(2018, 2027))
        rating = round(clipped_normal(rng, 7.2, 1.1, 4.5, 9.7), 1)
        episode_count = 1 if content_type == "Movie" else int(rng.integers(6, 25))
        episode_duration = int(rng.integers(25, 61))

        rows.append(
            {
                "show_id": f"SH{index:04d}",
                "title": fake.catch_phrase().title(),
                "genre": genre,
                "content_type": content_type,
                "language": rng.choice(LANGUAGES, p=[0.40, 0.25, 0.13, 0.12, 0.10]),
                "release_year": release_year,
                "rating": rating,
                "episode_count": episode_count,
                "episode_duration_minutes": episode_duration,
            }
        )

    return pd.DataFrame(rows)


def generate_subscribers(rng: np.random.Generator, fake: Faker) -> pd.DataFrame:
    """Create subscribers with personas that shape their later viewing behaviour."""
    persona_names = list(PERSONAS)
    persona_weights = [PERSONAS[persona]["weight"] for persona in persona_names]
    rows: list[dict[str, object]] = []

    for index in range(1, SUBSCRIBER_COUNT + 1):
        persona = str(rng.choice(persona_names, p=persona_weights))
        signup_date = REFERENCE_DATE - timedelta(days=int(rng.integers(30, 730)))
        country = rng.choice(["India", "United States", "United Kingdom", "Canada", "Australia"], p=[0.42, 0.25, 0.13, 0.10, 0.10])
        rows.append(
            {
                "user_id": f"US{index:05d}",
                "subscriber_name": fake.name(),
                "age": int(rng.integers(18, 66)),
                "country": country,
                "subscription_plan": rng.choice(PLANS, p=[0.28, 0.47, 0.25]),
                "signup_date": signup_date.isoformat(),
                "viewer_persona": persona,
                "preferred_genre": "Documentary" if persona == "Documentary Fan" else rng.choice(GENRES),
            }
        )

    return pd.DataFrame(rows)


def allocate_session_counts(subscribers: pd.DataFrame, rng: np.random.Generator) -> np.ndarray:
    """Assign each subscriber sessions while guaranteeing every subscriber appears."""
    base_counts = np.array(
        [max(1, rng.poisson(PERSONAS[persona]["sessions"])) for persona in subscribers["viewer_persona"]],
        dtype=int,
    )
    difference = SESSION_COUNT - int(base_counts.sum())

    if difference > 0:
        recipients = rng.choice(len(base_counts), size=difference, replace=True)
        np.add.at(base_counts, recipients, 1)
    elif difference < 0:
        removable = np.repeat(np.arange(len(base_counts)), np.maximum(base_counts - 1, 0))
        recipients = rng.choice(removable, size=abs(difference), replace=False)
        np.subtract.at(base_counts, recipients, 1)
    return base_counts


def generate_activity(
    subscribers: pd.DataFrame, content: pd.DataFrame, rng: np.random.Generator
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Generate session-level activity and derive historical retention from engagement."""
    rows: list[dict[str, object]] = []
    activity_number = 1
    session_counts = allocate_session_counts(subscribers, rng)
    content_by_genre = {genre: group for genre, group in content.groupby("genre")}

    for subscriber, count in zip(subscribers.itertuples(index=False), session_counts, strict=True):
        profile = PERSONAS[subscriber.viewer_persona]
        preferred_catalog = content_by_genre.get(subscriber.preferred_genre, content)

        for _ in range(count):
            catalog = preferred_catalog if rng.random() < 0.58 else content
            show = catalog.iloc[int(rng.integers(0, len(catalog)))]
            # A session is typically bounded by one episode; this produces realistic completion.
            completion_rate = round(clipped_normal(rng, profile["completion"], 18, 2, 100), 1)
            possible_minutes = max(8, show.episode_duration_minutes * completion_rate / 100)
            watch_duration = round(clipped_normal(rng, possible_minutes, 7, 2, show.episode_duration_minutes * 1.05), 1)
            pause_count = int(round(clipped_normal(rng, profile["pauses"] + (100 - completion_rate) / 75, 1.2, 0, 12)))
            watch_date = REFERENCE_DATE - timedelta(days=int(rng.integers(0, 181)))

            rows.append(
                {
                    "activity_id": f"AC{activity_number:06d}",
                    "user_id": subscriber.user_id,
                    "show_id": show.show_id,
                    "episode_number": int(rng.integers(1, show.episode_count + 1)),
                    "watch_date": watch_date.isoformat(),
                    "watch_duration_minutes": watch_duration,
                    "completion_rate": completion_rate,
                    "pause_count": pause_count,
                    "device": rng.choice(DEVICES, p=[0.46, 0.27, 0.17, 0.10]),
                }
            )
            activity_number += 1

    activity = pd.DataFrame(rows)
    user_metrics = activity.groupby("user_id").agg(
        average_completion_rate=("completion_rate", "mean"),
        average_watch_duration_minutes=("watch_duration_minutes", "mean"),
        average_pause_count=("pause_count", "mean"),
        session_frequency=("activity_id", "count"),
    )
    subscribers = subscribers.join(user_metrics, on="user_id")

    # Retention probability combines persona baseline with observed session behaviour.
    retention_probability = (
        subscribers["viewer_persona"].map(lambda persona: PERSONAS[persona]["retention"])
        + (subscribers["average_completion_rate"] - 60) * 0.0025
        + (subscribers["average_watch_duration_minutes"] - 30) * 0.0015
        + (subscribers["session_frequency"] - 8) * 0.0045
        - (subscribers["average_pause_count"] - 1.5) * 0.018
    ).clip(0.08, 0.94)
    subscribers["retained"] = rng.random(len(subscribers)) < retention_probability
    subscribers["retention_status"] = np.where(subscribers["retained"], "Retained", "Churned")
    subscribers.drop(columns="retained", inplace=True)

    return subscribers, activity


def validate_data(subscribers: pd.DataFrame, content: pd.DataFrame, activity: pd.DataFrame) -> None:
    """Fail fast if generated datasets violate their intended schema or relationships."""
    assert len(subscribers) == SUBSCRIBER_COUNT
    assert len(content) == CONTENT_COUNT
    assert len(activity) == SESSION_COUNT
    assert subscribers["user_id"].is_unique and content["show_id"].is_unique and activity["activity_id"].is_unique
    assert activity["user_id"].isin(subscribers["user_id"]).all()
    assert activity["show_id"].isin(content["show_id"]).all()
    assert activity["watch_duration_minutes"].gt(0).all()
    assert activity["completion_rate"].between(0, 100).all()
    assert activity["pause_count"].ge(0).all()


def main() -> None:
    """Generate and save the three raw project datasets."""
    rng = np.random.default_rng(SEED)
    fake = Faker()
    fake.seed_instance(SEED)
    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    content = generate_content(rng, fake)
    subscribers = generate_subscribers(rng, fake)
    subscribers, activity = generate_activity(subscribers, content, rng)
    validate_data(subscribers, content, activity)

    subscribers.to_csv(RAW_DATA_DIR / "subscriber_data.csv", index=False)
    content.to_csv(RAW_DATA_DIR / "content_metadata.csv", index=False)
    activity.to_csv(RAW_DATA_DIR / "viewer_activity.csv", index=False)

    print(f"Generated {len(subscribers):,} subscribers, {len(content):,} shows, and {len(activity):,} viewing sessions.")
    print(f"Raw data saved to: {RAW_DATA_DIR}")
    print(f"Retention rate: {(subscribers['retention_status'] == 'Retained').mean():.1%}")


if __name__ == "__main__":
    main()
