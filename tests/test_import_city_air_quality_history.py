from datetime import date

from scripts.import_city_air_quality_history import (
    DEFAULT_DATA_DIRECTORY,
    load_history_records,
)


def test_downloaded_hanoi_dataset_is_valid_for_import():
    records, skipped_empty_rows = load_history_records(DEFAULT_DATA_DIRECTORY)

    assert len(records) == 1295
    assert skipped_empty_rows == 3
    assert records[0]["observed_on"] == date(2022, 8, 4)
    assert records[-1]["observed_on"] == date(2026, 2, 18)
    assert records[0]["city"] == "Hanoi"
    assert records[0]["country"] == "Vietnam"
    assert records[0]["source"] == "Open-Meteo CAMS global"
    assert records[0]["data_class"] == "modeled"
    assert records[0]["license"] == "CC0-1.0"
    assert records[0]["us_aqi"] is None
    assert records[1]["us_aqi"] == 101.70588235294117
