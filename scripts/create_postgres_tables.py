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


create_city_air_quality_history_table_sql = """
CREATE TABLE IF NOT EXISTS city_air_quality_history (
    city_air_quality_history_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    source TEXT NOT NULL,
    source_dataset_id TEXT NOT NULL,
    license TEXT NOT NULL,
    data_class TEXT NOT NULL CHECK (data_class IN ('measured', 'modeled')),
    aggregation_period TEXT NOT NULL CHECK (aggregation_period IN ('hourly', 'daily_mean')),
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    observed_on DATE NOT NULL,
    city TEXT NOT NULL,
    country TEXT NOT NULL,
    country_code TEXT NOT NULL,
    admin1_code TEXT,
    admin2_code TEXT,
    geoname_id BIGINT,
    population BIGINT,
    longitude DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    pm2_5_ug_m3 DOUBLE PRECISION,
    pm10_ug_m3 DOUBLE PRECISION,
    nitrogen_dioxide_ug_m3 DOUBLE PRECISION,
    sulphur_dioxide_ug_m3 DOUBLE PRECISION,
    carbon_monoxide_ug_m3 DOUBLE PRECISION,
    ozone_ug_m3 DOUBLE PRECISION,
    us_aqi DOUBLE PRECISION,
    european_aqi DOUBLE PRECISION,
    uv_index DOUBLE PRECISION,
    aerosol_optical_depth DOUBLE PRECISION,
    dust_ug_m3 DOUBLE PRECISION,
    raw_response JSONB NOT NULL,

    UNIQUE (source_dataset_id, city, observed_on, aggregation_period)
);
"""


create_city_air_quality_history_index_sql = """
CREATE INDEX IF NOT EXISTS city_air_quality_history_city_date_index
ON city_air_quality_history (city, observed_on DESC);
"""


create_traffic_table_sql = """
CREATE TABLE IF NOT EXISTS traffic_observations (
    traffic_observation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    external_id TEXT NOT NULL UNIQUE,
    district_name TEXT NOT NULL,
    road_name TEXT NOT NULL,
    observed_at TIMESTAMPTZ NOT NULL,
    congestion_percent INTEGER NOT NULL CHECK (congestion_percent BETWEEN 0 AND 100),
    vehicle_count_estimate INTEGER,
    data_class TEXT NOT NULL CHECK (data_class IN ('verified', 'synthetic_demo')),
    notes TEXT NOT NULL,
    source TEXT,
    collected_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    longitude DOUBLE PRECISION NOT NULL,
    latitude DOUBLE PRECISION NOT NULL,
    current_speed_kmh DOUBLE PRECISION NOT NULL,
    free_flow_speed_kmh DOUBLE PRECISION NOT NULL,
    current_travel_time_seconds INTEGER NOT NULL,
    free_flow_travel_time_seconds INTEGER NOT NULL,
    confidence DOUBLE PRECISION,
    road_closure BOOLEAN NOT NULL DEFAULT FALSE,
    raw_response JSONB
);
"""


create_traffic_index_sql = """
CREATE INDEX IF NOT EXISTS traffic_observations_district_time_index
ON traffic_observations (district_name, observed_at DESC);
"""


migrate_traffic_columns_sql = """
ALTER TABLE traffic_observations ADD COLUMN IF NOT EXISTS source TEXT;
ALTER TABLE traffic_observations ADD COLUMN IF NOT EXISTS collected_at TIMESTAMPTZ;
ALTER TABLE traffic_observations ADD COLUMN IF NOT EXISTS longitude DOUBLE PRECISION;
ALTER TABLE traffic_observations ADD COLUMN IF NOT EXISTS latitude DOUBLE PRECISION;
ALTER TABLE traffic_observations ADD COLUMN IF NOT EXISTS current_speed_kmh DOUBLE PRECISION;
ALTER TABLE traffic_observations ADD COLUMN IF NOT EXISTS free_flow_speed_kmh DOUBLE PRECISION;
ALTER TABLE traffic_observations ADD COLUMN IF NOT EXISTS current_travel_time_seconds INTEGER;
ALTER TABLE traffic_observations ADD COLUMN IF NOT EXISTS free_flow_travel_time_seconds INTEGER;
ALTER TABLE traffic_observations ADD COLUMN IF NOT EXISTS confidence DOUBLE PRECISION;
ALTER TABLE traffic_observations ADD COLUMN IF NOT EXISTS road_closure BOOLEAN;
ALTER TABLE traffic_observations ADD COLUMN IF NOT EXISTS raw_response JSONB;
"""


migrate_district_columns_sql = """
ALTER TABLE air_quality_observations ADD COLUMN IF NOT EXISTS district_name TEXT;
ALTER TABLE weather_observations ADD COLUMN IF NOT EXISTS district_name TEXT;
ALTER TABLE modeled_air_quality_observations ADD COLUMN IF NOT EXISTS district_name TEXT;
"""


create_investigations_table_sql = """
CREATE TABLE IF NOT EXISTS investigations (
    investigation_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    district_name TEXT NOT NULL,
    prompt TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('awaiting_human_review', 'approved', 'rejected')),
    agent_model TEXT NOT NULL,
    report JSONB NOT NULL,
    datahub_context JSONB NOT NULL DEFAULT '{}'::jsonb,
    tool_trace JSONB NOT NULL DEFAULT '[]'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


create_investigation_evidence_table_sql = """
CREATE TABLE IF NOT EXISTS investigation_evidence (
    investigation_evidence_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    investigation_id BIGINT NOT NULL REFERENCES investigations(investigation_id) ON DELETE CASCADE,
    tool_name TEXT NOT NULL,
    tool_status TEXT NOT NULL,
    evidence JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


create_investigation_actions_table_sql = """
CREATE TABLE IF NOT EXISTS investigation_actions (
    investigation_action_id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    investigation_id BIGINT NOT NULL REFERENCES investigations(investigation_id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('awaiting_human_review', 'approved', 'rejected')),
    description TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);
"""


with psycopg.connect(database_url) as connection:
    with connection.cursor() as cursor:
        cursor.execute(create_table_sql)
        cursor.execute(create_index_sql)
        cursor.execute(create_weather_table_sql)
        cursor.execute(create_weather_index_sql)
        cursor.execute(create_modeled_air_quality_table_sql)
        cursor.execute(create_modeled_air_quality_index_sql)
        cursor.execute(create_city_air_quality_history_table_sql)
        cursor.execute(create_city_air_quality_history_index_sql)
        cursor.execute(create_traffic_table_sql)
        cursor.execute(migrate_traffic_columns_sql)
        cursor.execute(create_traffic_index_sql)
        cursor.execute(migrate_district_columns_sql)
        cursor.execute(create_investigations_table_sql)
        cursor.execute(create_investigation_evidence_table_sql)
        cursor.execute(create_investigation_actions_table_sql)


print("PostgreSQL tables created successfully")
print("Created table: air_quality_observations")
print("Created table: weather_observations")
print("Created table: modeled_air_quality_observations")
print("Created table: city_air_quality_history")
print("Created table: traffic_observations")
print("Created table: investigations")
print("Created table: investigation_evidence")
print("Created table: investigation_actions")
