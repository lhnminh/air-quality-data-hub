import duckdb
import pytest
from sqlalchemy import create_engine, inspect

import database


@pytest.fixture
def iqair_result() -> dict:
    return {
        "status": "success",
        "data": {
            "city": "Hanoi",
            "state": "Ha Noi",
            "country": "Vietnam",
            "location": {
                "type": "Point",
                "coordinates": [105.81881, 21.021938],
            },
            "current": {
                "pollution": {
                    "ts": "2026-07-23T07:00:00.000Z",
                    "aqius": 90,
                    "mainus": "p2",
                    "aqicn": 53,
                    "maincn": "p1",
                }
            },
        },
    }


@pytest.fixture
def temporary_database(tmp_path, monkeypatch, iqair_result):
    database_path = tmp_path / "test.duckdb"
    monkeypatch.setattr(database, "DATABASE_PATH", database_path)
    database.save_iqair_observation(iqair_result)
    return database_path


def test_save_observation_and_prevent_duplicate(
    temporary_database, iqair_result
):
    assert database.save_iqair_observation(iqair_result) is False

    with duckdb.connect(str(temporary_database), read_only=True) as connection:
        row = connection.execute(
            """
            SELECT city, state, aqi_us, main_pollutant
            FROM iqair_observations
            """
        ).fetchone()

    assert row == ("Hanoi", "Ha Noi", 90, "p2")


def test_table_is_visible_through_sqlalchemy(temporary_database):
    engine = create_engine(f"duckdb:///{temporary_database.as_posix()}")
    try:
        assert "iqair_observations" in inspect(engine).get_table_names()
    finally:
        engine.dispose()
