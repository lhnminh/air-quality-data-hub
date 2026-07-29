from datetime import date

import pytest

from scripts.backfill_district_air_quality_history import (
    aggregate_daily_response,
    date_chunks,
)


def test_date_chunks_include_the_full_requested_range():
    chunks = list(date_chunks(date(2026, 1, 1), date(2026, 1, 8), 3))

    assert chunks == [
        (date(2026, 1, 1), date(2026, 1, 3)),
        (date(2026, 1, 4), date(2026, 1, 6)),
        (date(2026, 1, 7), date(2026, 1, 8)),
    ]


def test_aggregate_daily_response_averages_values_and_skips_nulls():
    district = {
        "name": "Hoan Kiem",
        "latitude": 21.028,
        "longitude": 105.854,
        "map_x": "60%",
        "map_y": "55%",
    }
    result = {
        "latitude": 21.0,
        "longitude": 105.9,
        "timezone": "Asia/Bangkok",
        "timezone_abbreviation": "+07",
        "utc_offset_seconds": 25200,
        "hourly": {
            "time": [
                "2026-01-01T00:00",
                "2026-01-01T01:00",
                "2026-01-02T00:00",
            ],
            "us_aqi": [50, 70, 80],
            "pm2_5": [10, None, 30],
            "pm10": [20, 40, 60],
            "nitrogen_dioxide": [3, 5, 7],
            "sulphur_dioxide": [1, 3, 5],
            "carbon_monoxide": [100, 200, 300],
            "ozone": [30, 50, 70],
        },
    }

    records = aggregate_daily_response(result, district)

    assert len(records) == 2
    first = records[0]
    assert first["observed_on"] == date(2026, 1, 1)
    assert first["us_aqi"] == pytest.approx(60)
    assert first["pm2_5_ug_m3"] == pytest.approx(10)
    assert first["pm10_ug_m3"] == pytest.approx(30)
    assert first["sample_count"] == 2
    assert first["requested_latitude"] == pytest.approx(21.028)
    assert first["model_latitude"] == pytest.approx(21.0)


def test_aggregate_daily_response_rejects_misaligned_variables():
    district = {
        "name": "Hoan Kiem",
        "latitude": 21.028,
        "longitude": 105.854,
        "map_x": "60%",
        "map_y": "55%",
    }
    result = {
        "latitude": 21.0,
        "longitude": 105.9,
        "hourly": {
            "time": ["2026-01-01T00:00"],
            "us_aqi": [],
            "pm2_5": [10],
            "pm10": [20],
            "nitrogen_dioxide": [3],
            "sulphur_dioxide": [1],
            "carbon_monoxide": [100],
            "ozone": [30],
        },
    }

    with pytest.raises(ValueError, match="timestamps"):
        aggregate_daily_response(result, district)
