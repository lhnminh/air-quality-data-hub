from pathlib import Path

import duckdb
from sqlalchemy import create_engine, inspect


DATABASE_PATH = (
    Path(__file__).resolve().parents[1] / "data" / "airtrace.duckdb"
)


def main() -> None:
    if not DATABASE_PATH.exists():
        raise SystemExit(f"Database does not exist: {DATABASE_PATH}")

    print(f"Database: {DATABASE_PATH}")

    with duckdb.connect(str(DATABASE_PATH), read_only=True) as connection:
        print("\nTables")
        connection.sql("SHOW TABLES").show()

        print("\niqair_observations schema")
        connection.sql("DESCRIBE iqair_observations").show()

        print("\nLatest observations")
        connection.sql(
            """
            SELECT
                source,
                collected_at,
                observed_at,
                city,
                aqi_us,
                main_pollutant
            FROM iqair_observations
            ORDER BY observed_at DESC
            LIMIT 10
            """
        ).show()

    engine = create_engine(f"duckdb:///{DATABASE_PATH.as_posix()}")
    try:
        print(f"\nTables visible through SQLAlchemy: {inspect(engine).get_table_names()}")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
