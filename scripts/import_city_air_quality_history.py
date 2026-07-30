import argparse
import csv
import json
import os
from datetime import date
from pathlib import Path
from typing import Any

import psycopg
from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIRECTORY = PROJECT_ROOT / "data"
SOURCE = "Open-Meteo CAMS global"
DATA_CLASS = "modeled"
AGGREGATION_PERIOD = "daily_mean"
COUNTRY_NAMES = {"VN": "Vietnam"}

load_dotenv(PROJECT_ROOT / ".env")

MEASUREMENT_COLUMNS = (
    "pm10",
    "pm2_5",
    "carbon_monoxide",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "ozone",
    "aerosol_optical_depth",
    "dust",
    "uv_index",
    "us_aqi",
    "european_aqi",
)

INSERT_HISTORY_SQL = """
    INSERT INTO city_air_quality_history (
        source,
        source_dataset_id,
        license,
        data_class,
        aggregation_period,
        observed_on,
        city,
        country,
        country_code,
        admin1_code,
        admin2_code,
        geoname_id,
        population,
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
        dust_ug_m3,
        raw_response
    )
    VALUES (
        %(source)s,
        %(source_dataset_id)s,
        %(license)s,
        %(data_class)s,
        %(aggregation_period)s,
        %(observed_on)s,
        %(city)s,
        %(country)s,
        %(country_code)s,
        %(admin1_code)s,
        %(admin2_code)s,
        %(geoname_id)s,
        %(population)s,
        %(longitude)s,
        %(latitude)s,
        %(pm2_5_ug_m3)s,
        %(pm10_ug_m3)s,
        %(nitrogen_dioxide_ug_m3)s,
        %(sulphur_dioxide_ug_m3)s,
        %(carbon_monoxide_ug_m3)s,
        %(ozone_ug_m3)s,
        %(us_aqi)s,
        %(european_aqi)s,
        %(uv_index)s,
        %(aerosol_optical_depth)s,
        %(dust_ug_m3)s,
        %(raw_response)s::jsonb
    )
    ON CONFLICT (source_dataset_id, city, observed_on, aggregation_period)
    DO UPDATE SET
        source = EXCLUDED.source,
        license = EXCLUDED.license,
        data_class = EXCLUDED.data_class,
        country = EXCLUDED.country,
        country_code = EXCLUDED.country_code,
        admin1_code = EXCLUDED.admin1_code,
        admin2_code = EXCLUDED.admin2_code,
        geoname_id = EXCLUDED.geoname_id,
        population = EXCLUDED.population,
        longitude = EXCLUDED.longitude,
        latitude = EXCLUDED.latitude,
        pm2_5_ug_m3 = EXCLUDED.pm2_5_ug_m3,
        pm10_ug_m3 = EXCLUDED.pm10_ug_m3,
        nitrogen_dioxide_ug_m3 = EXCLUDED.nitrogen_dioxide_ug_m3,
        sulphur_dioxide_ug_m3 = EXCLUDED.sulphur_dioxide_ug_m3,
        carbon_monoxide_ug_m3 = EXCLUDED.carbon_monoxide_ug_m3,
        ozone_ug_m3 = EXCLUDED.ozone_ug_m3,
        us_aqi = EXCLUDED.us_aqi,
        european_aqi = EXCLUDED.european_aqi,
        uv_index = EXCLUDED.uv_index,
        aerosol_optical_depth = EXCLUDED.aerosol_optical_depth,
        dust_ug_m3 = EXCLUDED.dust_ug_m3,
        raw_response = EXCLUDED.raw_response
"""


def get_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set in .env")
    return database_url


def optional_float(value: str) -> float | None:
    stripped_value = value.strip()
    return float(stripped_value) if stripped_value else None


def load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as file:
        return json.load(file)


def load_single_city(path: Path) -> dict[str, str]:
    with path.open(encoding="utf-8", newline="") as file:
        cities = list(csv.DictReader(file))

    if len(cities) != 1:
        raise ValueError(f"Expected exactly one city in {path}; found {len(cities)}")

    return cities[0]


def load_history_records(data_directory: Path) -> tuple[list[dict[str, Any]], int]:
    metadata = load_json(data_directory / "dataset-metadata.json")
    city = load_single_city(data_directory / "city_info.csv")
    license_names = [item["name"] for item in metadata.get("licenses", [])]

    if not license_names:
        raise ValueError("The dataset metadata does not declare a license")

    country_code = city["country_code"].strip().upper()
    country = COUNTRY_NAMES.get(country_code)
    if not country:
        raise ValueError(f"No country name mapping is configured for {country_code}")

    history_path = data_directory / "air_quality_historical.csv"
    records: list[dict[str, Any]] = []
    skipped_empty_rows = 0
    seen_dates: set[date] = set()

    with history_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        missing_columns = {"date", *MEASUREMENT_COLUMNS} - set(reader.fieldnames or [])
        if missing_columns:
            raise ValueError(
                f"Historical CSV is missing columns: {', '.join(sorted(missing_columns))}"
            )

        for line_number, row in enumerate(reader, start=2):
            try:
                observed_on = date.fromisoformat(row["date"])
                measurements = {
                    column: optional_float(row[column])
                    for column in MEASUREMENT_COLUMNS
                }
            except (TypeError, ValueError) as error:
                raise ValueError(
                    f"Invalid value in {history_path} at line {line_number}: {error}"
                ) from error

            if observed_on in seen_dates:
                raise ValueError(f"Duplicate historical date: {observed_on.isoformat()}")
            seen_dates.add(observed_on)

            if all(value is None for value in measurements.values()):
                skipped_empty_rows += 1
                continue

            records.append(
                {
                    "source": SOURCE,
                    "source_dataset_id": metadata["id"],
                    "license": ", ".join(license_names),
                    "data_class": DATA_CLASS,
                    "aggregation_period": AGGREGATION_PERIOD,
                    "observed_on": observed_on,
                    "city": city["city_name"].strip(),
                    "country": country,
                    "country_code": country_code,
                    "admin1_code": city["admin1"].strip() or None,
                    "admin2_code": city["admin2"].strip() or None,
                    "geoname_id": int(city["geoname_id"]),
                    "population": int(city["population"]),
                    "longitude": float(city["longitude"]),
                    "latitude": float(city["latitude"]),
                    "pm2_5_ug_m3": measurements["pm2_5"],
                    "pm10_ug_m3": measurements["pm10"],
                    "nitrogen_dioxide_ug_m3": measurements["nitrogen_dioxide"],
                    "sulphur_dioxide_ug_m3": measurements["sulphur_dioxide"],
                    "carbon_monoxide_ug_m3": measurements["carbon_monoxide"],
                    "ozone_ug_m3": measurements["ozone"],
                    "us_aqi": measurements["us_aqi"],
                    "european_aqi": measurements["european_aqi"],
                    "uv_index": measurements["uv_index"],
                    "aerosol_optical_depth": measurements["aerosol_optical_depth"],
                    "dust_ug_m3": measurements["dust"],
                    "raw_response": json.dumps(row),
                }
            )

    if not records:
        raise ValueError("The historical CSV contains no importable measurements")

    return records, skipped_empty_rows


def import_records(records: list[dict[str, Any]]) -> None:
    with psycopg.connect(get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.executemany(INSERT_HISTORY_SQL, records)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate and optionally import daily city air-quality history."
    )
    parser.add_argument(
        "--data-directory",
        type=Path,
        default=DEFAULT_DATA_DIRECTORY,
        help="Directory containing the downloaded dataset package.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write validated records to DATABASE_URL. Without this flag, no database write occurs.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    records, skipped_empty_rows = load_history_records(args.data_directory)
    first_date = records[0]["observed_on"]
    last_date = records[-1]["observed_on"]

    print(f"Validated {len(records)} daily records for {records[0]['city']}")
    print(f"Coverage: {first_date} to {last_date}")
    print(f"Skipped {skipped_empty_rows} rows with no measurements")
    print(f"Source: {records[0]['source']} ({records[0]['data_class']})")
    print(f"License: {records[0]['license']}")

    if not args.apply:
        print("Validation only; the database was not changed. Add --apply to import these records.")
        return

    import_records(records)
    print(f"Imported {len(records)} records into city_air_quality_history")


if __name__ == "__main__":
    main()
