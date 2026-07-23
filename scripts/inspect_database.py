import os
from pprint import pprint

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


load_dotenv()

database_url = os.environ.get("DATABASE_URL")

if not database_url:
    raise SystemExit("DATABASE_URL is not set in .env")


def main() -> None:
    with psycopg.connect(
        database_url,
        row_factory=dict_row,
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user")
            database_information = cursor.fetchone()

            print("PostgreSQL database")
            print(f"Database: {database_information['current_database']}")
            print(f"User: {database_information['current_user']}")

            cursor.execute(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name
                """
            )
            tables = cursor.fetchall()

            print("\nTables")
            for table in tables:
                print(f"- {table['table_name']}")

            cursor.execute(
                """
                SELECT
                    column_name,
                    data_type,
                    is_nullable
                FROM information_schema.columns
                WHERE
                    table_schema = 'public'
                    AND table_name = 'air_quality_observations'
                ORDER BY ordinal_position
                """
            )
            columns = cursor.fetchall()

            print("\nair_quality_observations columns")
            for column in columns:
                nullable = (
                    "nullable"
                    if column["is_nullable"] == "YES"
                    else "required"
                )
                print(
                    f"- {column['column_name']}: "
                    f"{column['data_type']} ({nullable})"
                )

            cursor.execute(
                """
                SELECT
                    source,
                    collected_at,
                    observed_at,
                    city,
                    aqi_us,
                    main_pollutant
                FROM air_quality_observations
                ORDER BY observed_at DESC
                LIMIT 10
                """
            )
            observations = cursor.fetchall()

            print("\nLatest observations")
            if not observations:
                print("No observations found")
            else:
                for observation in observations:
                    pprint(dict(observation))

            cursor.execute(
                """
                SELECT
                    source,
                    collected_at,
                    observed_at,
                    temperature_c,
                    relative_humidity_percent,
                    precipitation_mm,
                    wind_speed_kmh,
                    wind_direction_degrees,
                    wind_gusts_kmh
                FROM weather_observations
                ORDER BY observed_at DESC
                LIMIT 10
                """
            )
            weather_observations = cursor.fetchall()

            print("\nLatest weather observations")
            if not weather_observations:
                print("No weather observations found")
            else:
                for observation in weather_observations:
                    pprint(dict(observation))

            cursor.execute(
                """
                SELECT
                    source,
                    collected_at,
                    observed_at,
                    us_aqi,
                    pm2_5_ug_m3,
                    pm10_ug_m3,
                    nitrogen_dioxide_ug_m3,
                    sulphur_dioxide_ug_m3,
                    carbon_monoxide_ug_m3,
                    ozone_ug_m3
                FROM modeled_air_quality_observations
                ORDER BY observed_at DESC
                LIMIT 10
                """
            )
            modeled_air_quality_observations = cursor.fetchall()

            print("\nLatest modeled air-quality observations")
            if not modeled_air_quality_observations:
                print("No modeled air-quality observations found")
            else:
                for observation in modeled_air_quality_observations:
                    pprint(dict(observation))


if __name__ == "__main__":
    main()
