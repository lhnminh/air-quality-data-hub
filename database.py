import json
from pathlib import Path
from typing import Any

import duckdb


DATABASE_PATH = Path(__file__).parent / "data" / "airtrace.duckdb"


def get_recent_observations(
    limit: int = 20, database_path: Path | None = None
) -> list[dict[str, Any]]:
    """Return recent air-quality rows in a browser-friendly format."""
    path = database_path or DATABASE_PATH
    if not path.exists():
        return []

    safe_limit = min(max(limit, 1), 100)

    with duckdb.connect(str(path), read_only=True) as connection:
        rows = connection.execute(
            """
            SELECT
                source,
                strftime(
                    timezone('UTC', collected_at),
                    '%Y-%m-%dT%H:%M:%SZ'
                ) AS collected_at,
                strftime(
                    timezone('UTC', observed_at),
                    '%Y-%m-%dT%H:%M:%SZ'
                ) AS observed_at,
                city,
                state,
                country,
                longitude,
                latitude,
                aqi_us,
                main_pollutant
            FROM iqair_observations
            ORDER BY observed_at DESC
            LIMIT ?
            """,
            [safe_limit],
        ).fetchall()

        column_names = [column[0] for column in connection.description]

    return [dict(zip(column_names, row)) for row in rows]


def save_iqair_observation(result: dict[str, Any]) -> bool:
    data = result["data"]
    pollution = data["current"]["pollution"]
    longitude, latitude = data["location"]["coordinates"]

    DATABASE_PATH.parent.mkdir(exist_ok=True)

    with duckdb.connect(str(DATABASE_PATH)) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS iqair_observations (
                source VARCHAR NOT NULL,
                collected_at TIMESTAMPTZ NOT NULL,
                observed_at TIMESTAMPTZ NOT NULL,
                city VARCHAR NOT NULL,
                state VARCHAR NOT NULL,
                country VARCHAR NOT NULL,
                longitude DOUBLE NOT NULL,
                latitude DOUBLE NOT NULL,
                aqi_us INTEGER NOT NULL,
                main_pollutant VARCHAR NOT NULL,
                raw_response JSON NOT NULL,
                PRIMARY KEY (source, city, observed_at)
            )
            """
        )

        inserted_row = connection.execute(
            """
            INSERT INTO iqair_observations VALUES (
                ?, current_timestamp, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            ON CONFLICT DO NOTHING
            RETURNING 1
            """,
            [
                "IQAir",
                pollution["ts"],
                data["city"],
                data["state"],
                data["country"],
                longitude,
                latitude,
                pollution["aqius"],
                pollution["mainus"],
                json.dumps(result),
            ],
        ).fetchone()

    return inserted_row is not None
