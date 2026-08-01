import argparse
import json
import os
import sys
import time
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any, Iterable
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import psycopg
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from districts import DISTRICTS, District


OPEN_METEO_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
SOURCE = "Open-Meteo CAMS global daily mean"
ATTRIBUTION = "Open-Meteo; Copernicus Atmosphere Monitoring Service (CAMS)"
MODEL_DOMAIN = "cams_global"
DATA_CLASS = "modeled"
AGGREGATION_PERIOD = "daily_mean"
DEFAULT_START_DATE = date(2022, 8, 1)
DEFAULT_END_DATE = date.today() - timedelta(days=1)
HOURLY_VARIABLES = (
    "us_aqi",
    "pm2_5",
    "pm10",
    "nitrogen_dioxide",
    "sulphur_dioxide",
    "carbon_monoxide",
    "ozone",
)

load_dotenv(PROJECT_ROOT / ".env")


INSERT_HISTORY_SQL = """
    INSERT INTO district_air_quality_history (
        source,
        attribution,
        model_domain,
        data_class,
        aggregation_period,
        observed_on,
        district_name,
        requested_longitude,
        requested_latitude,
        model_longitude,
        model_latitude,
        pm2_5_ug_m3,
        pm10_ug_m3,
        nitrogen_dioxide_ug_m3,
        sulphur_dioxide_ug_m3,
        carbon_monoxide_ug_m3,
        ozone_ug_m3,
        us_aqi,
        sample_count,
        raw_response
    )
    VALUES (
        %(source)s,
        %(attribution)s,
        %(model_domain)s,
        %(data_class)s,
        %(aggregation_period)s,
        %(observed_on)s,
        %(district_name)s,
        %(requested_longitude)s,
        %(requested_latitude)s,
        %(model_longitude)s,
        %(model_latitude)s,
        %(pm2_5_ug_m3)s,
        %(pm10_ug_m3)s,
        %(nitrogen_dioxide_ug_m3)s,
        %(sulphur_dioxide_ug_m3)s,
        %(carbon_monoxide_ug_m3)s,
        %(ozone_ug_m3)s,
        %(us_aqi)s,
        %(sample_count)s,
        %(raw_response)s::jsonb
    )
    ON CONFLICT (source, district_name, observed_on)
    DO UPDATE SET
        collected_at = CURRENT_TIMESTAMP,
        attribution = EXCLUDED.attribution,
        model_domain = EXCLUDED.model_domain,
        data_class = EXCLUDED.data_class,
        aggregation_period = EXCLUDED.aggregation_period,
        requested_longitude = EXCLUDED.requested_longitude,
        requested_latitude = EXCLUDED.requested_latitude,
        model_longitude = EXCLUDED.model_longitude,
        model_latitude = EXCLUDED.model_latitude,
        pm2_5_ug_m3 = EXCLUDED.pm2_5_ug_m3,
        pm10_ug_m3 = EXCLUDED.pm10_ug_m3,
        nitrogen_dioxide_ug_m3 = EXCLUDED.nitrogen_dioxide_ug_m3,
        sulphur_dioxide_ug_m3 = EXCLUDED.sulphur_dioxide_ug_m3,
        carbon_monoxide_ug_m3 = EXCLUDED.carbon_monoxide_ug_m3,
        ozone_ug_m3 = EXCLUDED.ozone_ug_m3,
        us_aqi = EXCLUDED.us_aqi,
        sample_count = EXCLUDED.sample_count,
        raw_response = EXCLUDED.raw_response
"""


def parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Expected a date in YYYY-MM-DD format") from error


def get_database_url() -> str:
    database_url = os.environ.get("DATABASE_URL")
    if not database_url:
        raise RuntimeError("DATABASE_URL is not set in .env")
    return database_url


def date_chunks(
    start_date: date,
    end_date: date,
    chunk_days: int,
) -> Iterable[tuple[date, date]]:
    chunk_start = start_date
    while chunk_start <= end_date:
        chunk_end = min(chunk_start + timedelta(days=chunk_days - 1), end_date)
        yield chunk_start, chunk_end
        chunk_start = chunk_end + timedelta(days=1)


def request_history(
    districts: list[District],
    start_date: date,
    end_date: date,
) -> list[dict[str, Any]]:
    query = urlencode(
        {
            "latitude": ",".join(str(district["latitude"]) for district in districts),
            "longitude": ",".join(str(district["longitude"]) for district in districts),
            "hourly": ",".join(HOURLY_VARIABLES),
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "domains": MODEL_DOMAIN,
            "timezone": "Asia/Bangkok",
        }
    )
    request = Request(
        f"{OPEN_METEO_AIR_QUALITY_URL}?{query}",
        headers={"User-Agent": "AerX/0.1 district-history-backfill"},
    )

    for attempt in range(3):
        try:
            with urlopen(request, timeout=60) as response:
                result = json.load(response)
            break
        except HTTPError as error:
            message = error.read().decode("utf-8", errors="replace")
            if attempt == 2 or error.code < 500:
                raise RuntimeError(
                    f"Open-Meteo returned HTTP {error.code}: {message}"
                ) from None
        except URLError as error:
            if attempt == 2:
                raise RuntimeError(f"Could not reach Open-Meteo: {error.reason}") from None

        time.sleep(2**attempt)

    results = result if isinstance(result, list) else [result]
    if len(results) != len(districts):
        raise ValueError(
            f"Expected {len(districts)} location responses; received {len(results)}"
        )
    return results


def mean(values: list[float]) -> float | None:
    return sum(values) / len(values) if values else None


def aggregate_daily_response(
    result: dict[str, Any],
    district: District,
) -> list[dict[str, Any]]:
    hourly = result.get("hourly") or {}
    times = hourly.get("time") or []
    missing_variables = set(HOURLY_VARIABLES) - set(hourly)
    if missing_variables:
        raise ValueError(
            f"{district['name']} response is missing: "
            f"{', '.join(sorted(missing_variables))}"
        )

    for variable in HOURLY_VARIABLES:
        if len(hourly[variable]) != len(times):
            raise ValueError(
                f"{district['name']} has {len(times)} timestamps but "
                f"{len(hourly[variable])} {variable} values"
            )

    daily_values: dict[str, dict[str, list[float]]] = defaultdict(
        lambda: {variable: [] for variable in HOURLY_VARIABLES}
    )
    daily_sample_times: dict[str, set[str]] = defaultdict(set)

    for index, timestamp in enumerate(times):
        observed_on = timestamp[:10]
        row_has_value = False
        for variable in HOURLY_VARIABLES:
            value = hourly[variable][index]
            if value is not None:
                daily_values[observed_on][variable].append(float(value))
                row_has_value = True
        if row_has_value:
            daily_sample_times[observed_on].add(timestamp)

    records: list[dict[str, Any]] = []
    for observed_on in sorted(daily_values):
        values = daily_values[observed_on]
        sample_count = len(daily_sample_times[observed_on])
        if not sample_count:
            continue

        metric_counts = {
            variable: len(variable_values)
            for variable, variable_values in values.items()
        }
        records.append(
            {
                "source": SOURCE,
                "attribution": ATTRIBUTION,
                "model_domain": MODEL_DOMAIN,
                "data_class": DATA_CLASS,
                "aggregation_period": AGGREGATION_PERIOD,
                "observed_on": date.fromisoformat(observed_on),
                "district_name": district["name"],
                "requested_longitude": district["longitude"],
                "requested_latitude": district["latitude"],
                "model_longitude": float(result["longitude"]),
                "model_latitude": float(result["latitude"]),
                "pm2_5_ug_m3": mean(values["pm2_5"]),
                "pm10_ug_m3": mean(values["pm10"]),
                "nitrogen_dioxide_ug_m3": mean(values["nitrogen_dioxide"]),
                "sulphur_dioxide_ug_m3": mean(values["sulphur_dioxide"]),
                "carbon_monoxide_ug_m3": mean(values["carbon_monoxide"]),
                "ozone_ug_m3": mean(values["ozone"]),
                "us_aqi": mean(values["us_aqi"]),
                "sample_count": sample_count,
                "raw_response": json.dumps(
                    {
                        "source_url": OPEN_METEO_AIR_QUALITY_URL,
                        "model_domain": MODEL_DOMAIN,
                        "timezone": result.get("timezone"),
                        "timezone_abbreviation": result.get("timezone_abbreviation"),
                        "utc_offset_seconds": result.get("utc_offset_seconds"),
                        "metric_sample_counts": metric_counts,
                    }
                ),
            }
        )

    return records


def import_records(records: list[dict[str, Any]]) -> None:
    with psycopg.connect(get_database_url()) as connection:
        with connection.cursor() as cursor:
            cursor.executemany(INSERT_HISTORY_SQL, records)


def selected_districts(names: list[str] | None) -> list[District]:
    if not names:
        return DISTRICTS
    requested_names = set(names)
    return [district for district in DISTRICTS if district["name"] in requested_names]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Backfill daily CAMS air-quality history for Hanoi pilot districts."
    )
    parser.add_argument("--start-date", type=parse_date, default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", type=parse_date, default=DEFAULT_END_DATE)
    parser.add_argument("--chunk-days", type=int, default=90, choices=range(7, 367))
    parser.add_argument(
        "--district",
        action="append",
        choices=[district["name"] for district in DISTRICTS],
        help="Backfill only a named district. Repeat to select multiple districts.",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write records to DATABASE_URL. Without this flag, the database is unchanged.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.start_date > args.end_date:
        raise SystemExit("--start-date must be on or before --end-date")

    districts = selected_districts(args.district)
    records: list[dict[str, Any]] = []
    for chunk_start, chunk_end in date_chunks(
        args.start_date,
        args.end_date,
        args.chunk_days,
    ):
        print(f"Fetching {chunk_start} to {chunk_end} for {len(districts)} districts")
        results = request_history(districts, chunk_start, chunk_end)
        for district, result in zip(districts, results, strict=True):
            records.extend(aggregate_daily_response(result, district))

    if not records:
        raise SystemExit("Open-Meteo returned no importable district history")

    print(
        f"Validated {len(records)} daily records across {len(districts)} districts "
        f"from {min(row['observed_on'] for row in records)} "
        f"to {max(row['observed_on'] for row in records)}"
    )
    if not args.apply:
        print("Validation only; the database was not changed. Add --apply to import.")
        return

    import_records(records)
    print(f"Imported or refreshed {len(records)} district daily records in the database")


if __name__ == "__main__":
    main()
