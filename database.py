import json
import os
from typing import Any

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv

from districts import DISTRICTS


load_dotenv()


def get_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL is not set in .env")

    return database_url

def check_database_connection() -> bool:
    try:
        with psycopg.connect(get_database_url()) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                cursor.fetchone()

        return True
    except (psycopg.Error, RuntimeError):
        return False


def get_recent_observations(limit: int = 20) -> list[dict[str, Any]]:
    safe_limit = min(max(limit, 1), 100)

    query = """
        SELECT
            source,
            district_name,
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


def get_recent_weather_observations(limit: int = 20) -> list[dict[str, Any]]:
    safe_limit = min(max(limit, 1), 100)

    query = """
        SELECT
            source,
            collected_at,
            observed_at,
            longitude,
            latitude,
            temperature_c,
            relative_humidity_percent,
            precipitation_mm,
            weather_code,
            wind_speed_kmh,
            wind_direction_degrees,
            wind_gusts_kmh
        FROM weather_observations
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


def get_recent_modeled_air_quality_observations(
    limit: int = 20,
) -> list[dict[str, Any]]:
    safe_limit = min(max(limit, 1), 100)

    query = """
        SELECT
            source,
            collected_at,
            observed_at,
            longitude,
            latitude,
            us_aqi,
            pm2_5_ug_m3,
            pm10_ug_m3,
            nitrogen_dioxide_ug_m3,
            sulphur_dioxide_ug_m3,
            carbon_monoxide_ug_m3,
            ozone_ug_m3
        FROM modeled_air_quality_observations
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


def get_district_statuses() -> list[dict[str, Any]]:
    query = """
        WITH latest_weather AS (
            SELECT DISTINCT ON (district_name)
                district_name,
                observed_at AS weather_observed_at,
                wind_speed_kmh,
                wind_direction_degrees,
                wind_gusts_kmh,
                temperature_c,
                relative_humidity_percent,
                precipitation_mm
            FROM weather_observations
            WHERE district_name IS NOT NULL
            ORDER BY district_name, observed_at DESC
        ),
        latest_air_quality AS (
            SELECT DISTINCT ON (district_name)
                district_name,
                observed_at AS air_quality_observed_at,
                us_aqi,
                pm2_5_ug_m3,
                pm10_ug_m3,
                nitrogen_dioxide_ug_m3,
                sulphur_dioxide_ug_m3,
                carbon_monoxide_ug_m3,
                ozone_ug_m3
            FROM modeled_air_quality_observations
            WHERE district_name IS NOT NULL
            ORDER BY district_name, observed_at DESC
        )
        SELECT
            COALESCE(weather.district_name, air_quality.district_name) AS district_name,
            weather.weather_observed_at,
            weather.wind_speed_kmh,
            weather.wind_direction_degrees,
            weather.wind_gusts_kmh,
            weather.temperature_c,
            weather.relative_humidity_percent,
            weather.precipitation_mm,
            air_quality.air_quality_observed_at,
            air_quality.us_aqi,
            air_quality.pm2_5_ug_m3,
            air_quality.pm10_ug_m3,
            air_quality.nitrogen_dioxide_ug_m3,
            air_quality.sulphur_dioxide_ug_m3,
            air_quality.carbon_monoxide_ug_m3,
            air_quality.ozone_ug_m3
        FROM latest_weather AS weather
        FULL OUTER JOIN latest_air_quality AS air_quality
            ON weather.district_name = air_quality.district_name
        ORDER BY district_name
    """

    with psycopg.connect(get_database_url(), row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query)
            rows = cursor.fetchall()

    rows_by_district = {row["district_name"]: dict(row) for row in rows}

    statuses = [
        {
            "district_name": district["name"],
            "latitude": district["latitude"],
            "longitude": district["longitude"],
            **rows_by_district.get(district["name"], {}),
        }
        for district in DISTRICTS
    ]

    required_fields = (
        "weather_observed_at",
        "wind_speed_kmh",
        "wind_direction_degrees",
        "wind_gusts_kmh",
        "temperature_c",
        "relative_humidity_percent",
        "precipitation_mm",
        "air_quality_observed_at",
        "us_aqi",
        "pm2_5_ug_m3",
        "pm10_ug_m3",
        "nitrogen_dioxide_ug_m3",
        "sulphur_dioxide_ug_m3",
        "carbon_monoxide_ug_m3",
        "ozone_ug_m3",
    )
    return [
        status
        for status in statuses
        if all(status.get(field) is not None for field in required_fields)
    ]


def save_open_meteo_weather_observation(
    result: dict[str, Any],
    district_name: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> bool:
    current = result["current"]

    query = """
        INSERT INTO weather_observations (
            source,
            district_name,
            collected_at,
            observed_at,
            longitude,
            latitude,
            temperature_c,
            relative_humidity_percent,
            precipitation_mm,
            weather_code,
            wind_speed_kmh,
            wind_direction_degrees,
            wind_gusts_kmh,
            raw_response
        )
        VALUES (
            %s,
            %s,
            CURRENT_TIMESTAMP,
            to_timestamp(%s),
            %s,
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
        ON CONFLICT (source, latitude, longitude, observed_at)
        DO UPDATE SET
            district_name = EXCLUDED.district_name,
            collected_at = EXCLUDED.collected_at,
            temperature_c = EXCLUDED.temperature_c,
            relative_humidity_percent = EXCLUDED.relative_humidity_percent,
            precipitation_mm = EXCLUDED.precipitation_mm,
            weather_code = EXCLUDED.weather_code,
            wind_speed_kmh = EXCLUDED.wind_speed_kmh,
            wind_direction_degrees = EXCLUDED.wind_direction_degrees,
            wind_gusts_kmh = EXCLUDED.wind_gusts_kmh,
            raw_response = EXCLUDED.raw_response
        RETURNING weather_observation_id
    """

    values = [
        "Open-Meteo",
        district_name,
        current["time"],
        longitude if longitude is not None else result["longitude"],
        latitude if latitude is not None else result["latitude"],
        current["temperature_2m"],
        current["relative_humidity_2m"],
        current["precipitation"],
        current["weather_code"],
        current["wind_speed_10m"],
        round(current["wind_direction_10m"]),
        current["wind_gusts_10m"],
        json.dumps(result),
    ]

    with psycopg.connect(get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, values)
            inserted_row = cursor.fetchone()

    return inserted_row is not None


def save_open_meteo_air_quality_observation(
    result: dict[str, Any],
    district_name: str | None = None,
    latitude: float | None = None,
    longitude: float | None = None,
) -> bool:
    current = result["current"]

    query = """
        INSERT INTO modeled_air_quality_observations (
            source,
            district_name,
            collected_at,
            observed_at,
            longitude,
            latitude,
            us_aqi,
            pm2_5_ug_m3,
            pm10_ug_m3,
            nitrogen_dioxide_ug_m3,
            sulphur_dioxide_ug_m3,
            carbon_monoxide_ug_m3,
            ozone_ug_m3,
            raw_response
        )
        VALUES (
            %s,
            %s,
            CURRENT_TIMESTAMP,
            to_timestamp(%s),
            %s,
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
        ON CONFLICT (source, latitude, longitude, observed_at)
        DO UPDATE SET
            district_name = EXCLUDED.district_name,
            collected_at = EXCLUDED.collected_at,
            us_aqi = EXCLUDED.us_aqi,
            pm2_5_ug_m3 = EXCLUDED.pm2_5_ug_m3,
            pm10_ug_m3 = EXCLUDED.pm10_ug_m3,
            nitrogen_dioxide_ug_m3 = EXCLUDED.nitrogen_dioxide_ug_m3,
            sulphur_dioxide_ug_m3 = EXCLUDED.sulphur_dioxide_ug_m3,
            carbon_monoxide_ug_m3 = EXCLUDED.carbon_monoxide_ug_m3,
            ozone_ug_m3 = EXCLUDED.ozone_ug_m3,
            raw_response = EXCLUDED.raw_response
        RETURNING modeled_air_quality_observation_id
    """

    values = [
        "Open-Meteo CAMS model",
        district_name,
        current["time"],
        longitude if longitude is not None else result["longitude"],
        latitude if latitude is not None else result["latitude"],
        round(current["us_aqi"]),
        current["pm2_5"],
        current["pm10"],
        current["nitrogen_dioxide"],
        current["sulphur_dioxide"],
        current["carbon_monoxide"],
        current["ozone"],
        json.dumps(result),
    ]

    with psycopg.connect(get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, values)
            inserted_row = cursor.fetchone()

    return inserted_row is not None
