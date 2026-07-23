from unittest.mock import MagicMock

import pytest

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
def fake_cursor(monkeypatch):
    cursor = MagicMock()

    connection = MagicMock()
    connection.__enter__.return_value = connection
    connection.cursor.return_value.__enter__.return_value = cursor

    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql://test-user:test-password@test-host/test-database",
    )
    monkeypatch.setattr(
        database.psycopg,
        "connect",
        MagicMock(return_value=connection),
    )

    return cursor


def test_save_observation(fake_cursor, iqair_result):
    fake_cursor.fetchone.return_value = (1,)

    inserted = database.save_iqair_observation(iqair_result)

    assert inserted is True

    query, values = fake_cursor.execute.call_args.args

    assert "INSERT INTO air_quality_observations" in query
    assert values[0] == "IQAir"
    assert values[2] == "Hanoi"
    assert values[7] == 90
    assert values[8] == "p2"


def test_duplicate_observation_is_not_inserted(
    fake_cursor,
    iqair_result,
):
    fake_cursor.fetchone.return_value = None

    inserted = database.save_iqair_observation(iqair_result)

    assert inserted is False


def test_get_recent_observations(fake_cursor):
    fake_cursor.fetchall.return_value = [
        {
            "source": "IQAir",
            "city": "Hanoi",
            "country": "Vietnam",
            "aqi_us": 90,
            "main_pollutant": "p2",
        }
    ]

    observations = database.get_recent_observations(limit=10)

    assert len(observations) == 1
    assert observations[0]["city"] == "Hanoi"
    assert observations[0]["aqi_us"] == 90
    assert observations[0]["main_pollutant"] == "p2"


def test_database_connection_check(fake_cursor):
    fake_cursor.fetchone.return_value = (1,)

    assert database.check_database_connection() is True