import os

import psycopg
from dotenv import load_dotenv


load_dotenv()

database_url = os.environ.get("DATABASE_URL")

if not database_url:
    raise SystemExit("DATABASE_URL is not set in .env")


create_table_sql = """
CREATE TABLE IF NOT EXISTS air_quality_observations (
    observation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source TEXT NOT NULL,
    district_name TEXT,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    observed_at TIMESTAMPTZ NOT NULL,
    city TEXT NOT NULL,
    state TEXT NOT NULL,
    country TEXT NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    aqi_us INTEGER NOT NULL,
    main_pollutant TEXT NOT NULL,
    raw_response JSONB NOT NULL,

    UNIQUE (source, city, observed_at)
);
"""


create_index_sql = """
CREATE INDEX IF NOT EXISTS observations_city_time_index
ON air_quality_observations (city, observed_at DESC);
"""


create_weather_table_sql = """
CREATE TABLE IF NOT EXISTS weather_observations (
    weather_observation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source TEXT NOT NULL,
    district_name TEXT,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    observed_at TIMESTAMPTZ NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    temperature_c DOUBLE PRECISION NOT NULL,
    relative_humidity_percent DOUBLE PRECISION NOT NULL,
    precipitation_mm DOUBLE PRECISION NOT NULL,
    weather_code INTEGER NOT NULL,
    wind_speed_kmh DOUBLE PRECISION NOT NULL,
    wind_direction_degrees INTEGER NOT NULL,
    wind_gusts_kmh DOUBLE PRECISION NOT NULL,
    raw_response JSONB NOT NULL,

    UNIQUE (source, latitude, longitude, observed_at)
);
"""


create_weather_index_sql = """
CREATE INDEX IF NOT EXISTS weather_observations_time_index
ON weather_observations (observed_at DESC);
"""


create_modeled_air_quality_table_sql = """
CREATE TABLE IF NOT EXISTS modeled_air_quality_observations (
    modeled_air_quality_observation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source TEXT NOT NULL,
    district_name TEXT,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    observed_at TIMESTAMPTZ NOT NULL,
    longitude DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    us_aqi INTEGER NOT NULL,
    pm2_5_ug_m3 DOUBLE PRECISION NOT NULL,
    pm10_ug_m3 DOUBLE PRECISION NOT NULL,
    nitrogen_dioxide_ug_m3 DOUBLE PRECISION NOT NULL,
    sulphur_dioxide_ug_m3 DOUBLE PRECISION NOT NULL,
    carbon_monoxide_ug_m3 DOUBLE PRECISION NOT NULL,
    ozone_ug_m3 DOUBLE PRECISION NOT NULL,
    raw_response JSONB NOT NULL,

    UNIQUE (source, latitude, longitude, observed_at)
);
"""


create_modeled_air_quality_index_sql = """
CREATE INDEX IF NOT EXISTS modeled_air_quality_observations_time_index
ON modeled_air_quality_observations (observed_at DESC);
"""


migrate_district_columns_sql = """
ALTER TABLE air_quality_observations ADD COLUMN IF NOT EXISTS district_name TEXT;
ALTER TABLE weather_observations ADD COLUMN IF NOT EXISTS district_name TEXT;
ALTER TABLE modeled_air_quality_observations ADD COLUMN IF NOT EXISTS district_name TEXT;
"""


with psycopg.connect(database_url) as connection:
    with connection.cursor() as cursor:
        cursor.execute(create_table_sql)
        cursor.execute(create_index_sql)
        cursor.execute(create_weather_table_sql)
        cursor.execute(create_weather_index_sql)
        cursor.execute(create_modeled_air_quality_table_sql)
        cursor.execute(create_modeled_air_quality_index_sql)
        cursor.execute(migrate_district_columns_sql)


print("PostgreSQL tables created successfully")
print("Created table: air_quality_observations")
print("Created table: weather_observations")
print("Created table: modeled_air_quality_observations")
