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


with psycopg.connect(database_url) as connection:
    with connection.cursor() as cursor:
        cursor.execute(create_table_sql)
        cursor.execute(create_index_sql)


print("PostgreSQL tables created successfully")
print("Created table: air_quality_observations")