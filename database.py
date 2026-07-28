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


def get_city_air_quality_history(
    city: str,
    days: int = 30,
) -> list[dict[str, Any]]:
    """Return the latest available daily city history in chronological order."""
    safe_days = min(max(days, 1), 3660)

    query = """
        WITH latest_history AS (
            SELECT
                source,
                source_dataset_id,
                license,
                data_class,
                aggregation_period,
                observed_on,
                city,
                country,
                country_code,
                longitude,
                latitude,
                pm2_5_ug_m3,
                pm10_ug_m3,
                nitrogen_dioxide_ug_m3,
                sulphur_dioxide_ug_m3,
                carbon_monoxide_ug_m3,
                ozone_ug_m3,
                us_aqi,
                european_aqi,
                uv_index,
                aerosol_optical_depth,
                dust_ug_m3
            FROM city_air_quality_history
            WHERE LOWER(city) = LOWER(%s)
            ORDER BY observed_on DESC
            LIMIT %s
        )
        SELECT *
        FROM latest_history
        ORDER BY observed_on ASC
    """

    with psycopg.connect(
        get_database_url(),
        row_factory=dict_row,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, [city.strip(), safe_days])
            rows = cursor.fetchall()

    return [dict(row) for row in rows]


def get_recent_traffic_observations(limit: int = 20) -> list[dict[str, Any]]:
    safe_limit = min(max(limit, 1), 100)

    query = """
        SELECT
            source,
            district_name,
            road_name,
            collected_at,
            observed_at,
            longitude,
            latitude,
            current_speed_kmh,
            free_flow_speed_kmh,
            congestion_percent,
            current_travel_time_seconds,
            free_flow_travel_time_seconds,
            confidence,
            road_closure
        FROM traffic_observations
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


def get_district_investigation_context(district_name: str) -> dict[str, Any] | None:
    """Return the latest bounded evidence package for one selected district."""
    query = """
        WITH district_air AS (
            SELECT
                observed_at AS district_air_observed_at,
                us_aqi AS district_us_aqi,
                pm2_5_ug_m3 AS district_pm2_5_ug_m3,
                pm10_ug_m3 AS district_pm10_ug_m3,
                nitrogen_dioxide_ug_m3 AS district_no2_ug_m3,
                sulphur_dioxide_ug_m3 AS district_so2_ug_m3,
                carbon_monoxide_ug_m3 AS district_co_ug_m3,
                ozone_ug_m3 AS district_ozone_ug_m3
            FROM modeled_air_quality_observations
            WHERE district_name = %s
            ORDER BY observed_at DESC
            LIMIT 1
        ),
        district_weather AS (
            SELECT
                observed_at AS weather_observed_at,
                wind_speed_kmh,
                wind_direction_degrees,
                wind_gusts_kmh,
                temperature_c,
                relative_humidity_percent,
                precipitation_mm
            FROM weather_observations
            WHERE district_name = %s
            ORDER BY observed_at DESC
            LIMIT 1
        ),
        district_traffic AS (
            SELECT
                observed_at AS traffic_observed_at,
                road_name AS traffic_road_name,
                current_speed_kmh AS traffic_current_speed_kmh,
                free_flow_speed_kmh AS traffic_free_flow_speed_kmh,
                congestion_percent AS traffic_congestion_percent,
                confidence AS traffic_confidence,
                road_closure AS traffic_road_closure
            FROM traffic_observations
            WHERE district_name = %s
            ORDER BY observed_at DESC
            LIMIT 1
        ),
        city_air AS (
            SELECT
                observed_at AS city_air_observed_at,
                aqi_us AS city_aqi_us,
                main_pollutant AS city_main_pollutant
            FROM air_quality_observations
            ORDER BY observed_at DESC
            LIMIT 1
        )
        SELECT
            %s AS district_name,
            district_air.*,
            district_weather.*,
            district_traffic.*,
            city_air.*
        FROM district_air
        FULL OUTER JOIN district_weather ON TRUE
        FULL OUTER JOIN district_traffic ON TRUE
        FULL OUTER JOIN city_air ON TRUE
    """
    with psycopg.connect(get_database_url(), row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, [district_name, district_name, district_name, district_name])
            row = cursor.fetchone()

    return dict(row) if row else None


def get_district_history(district_name: str, limit: int = 24) -> list[dict[str, Any]]:
    """Return a bounded district CAMS history for an investigation tool."""
    safe_limit = min(max(limit, 1), 48)
    query = """
        SELECT
            observed_at,
            us_aqi,
            pm2_5_ug_m3,
            nitrogen_dioxide_ug_m3,
            ozone_ug_m3
        FROM modeled_air_quality_observations
        WHERE district_name = %s
        ORDER BY observed_at DESC
        LIMIT %s
    """
    with psycopg.connect(get_database_url(), row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, [district_name, safe_limit])
            rows = cursor.fetchall()

    return [dict(row) for row in rows]


def save_investigation(
    district_name: str,
    prompt: str,
    agent_model: str,
    report: dict[str, Any],
    datahub_context: dict[str, Any],
    tool_trace: list[dict[str, Any]],
) -> dict[str, Any]:
    """Persist an agent result as an auditable, review-only investigation."""
    investigation_query = """
        INSERT INTO investigations (
            district_name, prompt, status, agent_model, report, datahub_context, tool_trace
        ) VALUES (%s, %s, 'awaiting_human_review', %s, %s::jsonb, %s::jsonb, %s::jsonb)
        RETURNING investigation_id, status, created_at
    """
    action_query = """
        INSERT INTO investigation_actions (
            investigation_id, action_type, status, description
        ) VALUES (%s, 'human_review', 'awaiting_human_review', %s)
        RETURNING action_type, status, description
    """
    evidence_query = """
        INSERT INTO investigation_evidence (
            investigation_id, tool_name, tool_status, evidence
        ) VALUES (%s, %s, %s, %s::jsonb)
    """
    action_description = (
        f"Review the AirTrace evidence package for {district_name} before any public alert "
        "or operational response."
    )
    with psycopg.connect(get_database_url(), row_factory=dict_row) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                investigation_query,
                [
                    district_name,
                    prompt,
                    agent_model,
                    json.dumps(report, default=str),
                    json.dumps(datahub_context, default=str),
                    json.dumps(tool_trace, default=str),
                ],
            )
            investigation = dict(cursor.fetchone())
            for tool in tool_trace:
                cursor.execute(
                    evidence_query,
                    [
                        investigation["investigation_id"],
                        tool["tool_name"],
                        tool["status"],
                        json.dumps(tool.get("evidence", {}), default=str),
                    ],
                )
            cursor.execute(
                action_query,
                [investigation["investigation_id"], action_description],
            )
            action = dict(cursor.fetchone())

    return {**investigation, "action": action}


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
        ),
        latest_traffic AS (
            SELECT DISTINCT ON (district_name)
                district_name,
                observed_at AS traffic_observed_at,
                road_name AS traffic_road_name,
                current_speed_kmh AS traffic_current_speed_kmh,
                free_flow_speed_kmh AS traffic_free_flow_speed_kmh,
                confidence AS traffic_confidence,
                road_closure AS traffic_road_closure
            FROM traffic_observations
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
            air_quality.ozone_ug_m3,
            traffic.traffic_observed_at,
            traffic.traffic_road_name,
            traffic.traffic_current_speed_kmh,
            traffic.traffic_free_flow_speed_kmh,
            traffic.traffic_confidence,
            traffic.traffic_road_closure
        FROM latest_weather AS weather
        FULL OUTER JOIN latest_air_quality AS air_quality
            ON weather.district_name = air_quality.district_name
        FULL OUTER JOIN latest_traffic AS traffic
            ON COALESCE(weather.district_name, air_quality.district_name) = traffic.district_name
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


def save_tomtom_traffic_observation(
    result: dict[str, Any],
    district_name: str,
    road_name: str,
    latitude: float,
    longitude: float,
    observed_at: str,
) -> bool:
    flow = result["flowSegmentData"]
    free_flow_speed = flow["freeFlowSpeed"]
    current_speed = flow["currentSpeed"]
    congestion_percent = (
        round(max(0, min(100, (1 - current_speed / free_flow_speed) * 100)))
        if free_flow_speed
        else 0
    )
    external_id = (
        f"tomtom:{district_name.lower().replace(' ', '-')}:"
        f"{road_name.lower().replace(' ', '-')}:{observed_at}"
    )
    query = """
        INSERT INTO traffic_observations (
            external_id,
            district_name,
            road_name,
            congestion_percent,
            data_class,
            notes,
            source,
            collected_at,
            observed_at,
            longitude,
            latitude,
            current_speed_kmh,
            free_flow_speed_kmh,
            current_travel_time_seconds,
            free_flow_travel_time_seconds,
            confidence,
            road_closure,
            raw_response
        )
        VALUES (
            %s, %s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP, %s, %s, %s, %s,
            %s, %s, %s, %s, %s, %s::jsonb
        )
        ON CONFLICT (external_id)
        DO UPDATE SET
            collected_at = EXCLUDED.collected_at,
            congestion_percent = EXCLUDED.congestion_percent,
            notes = EXCLUDED.notes,
            source = EXCLUDED.source,
            current_speed_kmh = EXCLUDED.current_speed_kmh,
            free_flow_speed_kmh = EXCLUDED.free_flow_speed_kmh,
            current_travel_time_seconds = EXCLUDED.current_travel_time_seconds,
            free_flow_travel_time_seconds = EXCLUDED.free_flow_travel_time_seconds,
            confidence = EXCLUDED.confidence,
            road_closure = EXCLUDED.road_closure,
            raw_response = EXCLUDED.raw_response
        RETURNING traffic_observation_id
    """
    values = [
        external_id,
        district_name,
        road_name,
        congestion_percent,
        "verified",
        "Real-time TomTom Traffic Flow at a representative major-road point.",
        "TomTom Traffic Flow",
        observed_at,
        longitude,
        latitude,
        current_speed,
        free_flow_speed,
        flow["currentTravelTime"],
        flow["freeFlowTravelTime"],
        flow.get("confidence"),
        flow.get("roadClosure", False),
        json.dumps(result),
    ]

    with psycopg.connect(get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.execute(query, values)
            inserted_row = cursor.fetchone()

    return inserted_row is not None
