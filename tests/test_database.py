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


def test_save_weather_observation(fake_cursor):
    fake_cursor.fetchone.return_value = (1,)
    weather_result = {
        "latitude": 21.028,
        "longitude": 105.834,
        "current": {
            "time": 1784815200,
            "temperature_2m": 31.2,
            "relative_humidity_2m": 70,
            "precipitation": 0.0,
            "weather_code": 2,
            "wind_speed_10m": 11.4,
            "wind_direction_10m": 120,
            "wind_gusts_10m": 18.2,
        },
    }

    inserted = database.save_open_meteo_weather_observation(weather_result)

    assert inserted is True
    query, values = fake_cursor.execute.call_args.args
    assert "INSERT INTO weather_observations" in query
    assert values[0] == "Open-Meteo"
    assert values[8] == 2
    assert values[9] == 11.4


def test_save_weather_observation_uses_requested_district_coordinates(fake_cursor):
    fake_cursor.fetchone.return_value = (1,)
    weather_result = {
        "latitude": 21.0,
        "longitude": 105.8,
        "current": {
            "time": 1784815200,
            "temperature_2m": 31.2,
            "relative_humidity_2m": 70,
            "precipitation": 0.0,
            "weather_code": 2,
            "wind_speed_10m": 11.4,
            "wind_direction_10m": 120,
            "wind_gusts_10m": 18.2,
        },
    }

    database.save_open_meteo_weather_observation(
        weather_result,
        "Ba Dinh",
        latitude=21.035,
        longitude=105.815,
    )

    _, values = fake_cursor.execute.call_args.args
    assert values[3] == 105.815
    assert values[4] == 21.035


def test_get_recent_weather_observations(fake_cursor):
    fake_cursor.fetchall.return_value = [
        {"source": "Open-Meteo", "wind_speed_kmh": 11.4}
    ]

    observations = database.get_recent_weather_observations(limit=10)

    assert observations[0]["source"] == "Open-Meteo"
    assert observations[0]["wind_speed_kmh"] == 11.4


def test_save_modeled_air_quality_observation(fake_cursor):
    fake_cursor.fetchone.return_value = (1,)
    air_quality_result = {
        "latitude": 21.028,
        "longitude": 105.834,
        "current": {
            "time": 1784815200,
            "us_aqi": 92,
            "pm2_5": 32.5,
            "pm10": 45.1,
            "nitrogen_dioxide": 19.2,
            "sulphur_dioxide": 4.0,
            "carbon_monoxide": 530.4,
            "ozone": 54.0,
        },
    }

    inserted = database.save_open_meteo_air_quality_observation(air_quality_result)

    assert inserted is True
    query, values = fake_cursor.execute.call_args.args
    assert "INSERT INTO modeled_air_quality_observations" in query
    assert values[0] == "Open-Meteo CAMS model"
    assert values[5] == 92
    assert values[6] == 32.5


def test_get_recent_modeled_air_quality_observations(fake_cursor):
    fake_cursor.fetchall.return_value = [
        {"source": "Open-Meteo CAMS model", "pm2_5_ug_m3": 32.5}
    ]

    observations = database.get_recent_modeled_air_quality_observations(limit=10)

    assert observations[0]["source"] == "Open-Meteo CAMS model"
    assert observations[0]["pm2_5_ug_m3"] == 32.5


def test_get_district_statuses(fake_cursor):
    fake_cursor.fetchall.return_value = [
        {
            "district_name": "Hoan Kiem",
            "weather_observed_at": "2026-07-23T07:30:00Z",
            "wind_speed_kmh": 10.8,
            "wind_direction_degrees": 120,
            "wind_gusts_kmh": 18.0,
            "temperature_c": 30.0,
            "relative_humidity_percent": 70.0,
            "precipitation_mm": 0.0,
            "air_quality_observed_at": "2026-07-23T07:00:00Z",
            "us_aqi": 97,
            "pm2_5_ug_m3": 35.0,
            "pm10_ug_m3": 48.0,
            "nitrogen_dioxide_ug_m3": 24.0,
            "sulphur_dioxide_ug_m3": 4.0,
            "carbon_monoxide_ug_m3": 530.0,
            "ozone_ug_m3": 50.0,
        }
    ]

    districts = database.get_district_statuses()

    hoan_kiem = next(
        district for district in districts if district["district_name"] == "Hoan Kiem"
    )

    assert len(districts) == 1
    assert hoan_kiem["us_aqi"] == 97
