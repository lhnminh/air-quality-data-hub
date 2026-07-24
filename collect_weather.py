import json
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from database import save_open_meteo_weather_observation
from districts import DISTRICTS


OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
HANOI_LATITUDE = 21.028
HANOI_LONGITUDE = 105.834
CURRENT_VARIABLES = ",".join(
    [
        "temperature_2m",
        "relative_humidity_2m",
        "precipitation",
        "weather_code",
        "wind_speed_10m",
        "wind_direction_10m",
        "wind_gusts_10m",
    ]
)


def get_current_weather(latitude: float, longitude: float) -> dict:
    query = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": CURRENT_VARIABLES,
            "wind_speed_unit": "kmh",
            "timeformat": "unixtime",
        }
    )

    try:
        with urlopen(f"{OPEN_METEO_FORECAST_URL}?{query}", timeout=10) as response:
            return json.load(response)
    except HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"Open-Meteo returned HTTP {error.code}: {message}") from None
    except URLError as error:
        raise SystemExit(f"Could not reach Open-Meteo: {error.reason}") from None


def main() -> None:
    failures = 0
    for district in DISTRICTS:
        try:
            result = get_current_weather(district["latitude"], district["longitude"])
        except SystemExit as error:
            failures += 1
            print(f"Skipped {district['name']}: {error}")
            continue

        observed_at = datetime.fromtimestamp(result["current"]["time"], UTC).isoformat()
        print(
            f"Collected Open-Meteo weather for {district['name']} at "
            f"{observed_at}: {result['current']['wind_speed_10m']} km/h wind"
        )
        if save_open_meteo_weather_observation(
            result,
            district["name"],
            latitude=district["latitude"],
            longitude=district["longitude"],
        ):
            print("Saved or refreshed weather observation in PostgreSQL")

    if failures:
        raise SystemExit(f"Weather collection finished with {failures} failed district(s)")


if __name__ == "__main__":
    main()
