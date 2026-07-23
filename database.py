import json
import os
from typing import Any

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


load_dotenv()


def get_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not set in .env")

    return database_url


def get_recent_observations(limit: int = 20) -> list[dict[str, Any]]:
    safe_limit = min(max(limit, 1), 100)

    query = """
        SELECT
            source,
            collected_at,
            observed_at,
            city,
            state,
            country,
            longitude,
            latitude,
            aqi_us,
            main_pollutant
        FROM air_quality_observations
        ORDER BY observed_at DESC
        LIMIT %s
    """

    with psycopg.connect(
        get_database_url(),
        row_factory=dict_row,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, [safe_limit])
            rows = cursor.fetchall()

    return [dict(row) for row in rows]


def save_iqair_observation(result: dict[str, Any]) -> bool:
    data = result["data"]
    pollution = data["current"]["pollution"]
    longitude, latitude = data["location"]["coordinates"]

    query = """
        INSERT INTO air_quality_observations (
            source,
            collected_at,
            observed_at,
            city,
            state,
            country,
            longitude,
            latitude,
            aqi_us,
            main_pollutant,
            raw_response
        )
        VALUES (
            %s,
            CURRENT_TIMESTAMP,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s,
            %s::jsonb
        )
        ON CONFLICT (source, city, observed_at)
        DO NOTHING
        RETURNING observation_id
    """

    values = [
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
    ]

    with psycopg.connect(get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, values)
            inserted_row = cursor.fetchone()

    return inserted_row is not None