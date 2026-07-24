import json
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from database import save_open_meteo_air_quality_observation
from districts import DISTRICTS


OPEN_METEO_AIR_QUALITY_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
CURRENT_VARIABLES = ",".join(
    [
        "us_aqi",
        "pm2_5",
        "pm10",
        "nitrogen_dioxide",
        "sulphur_dioxide",
        "carbon_monoxide",
        "ozone",
    ]
)


def get_current_air_quality(latitude: float, longitude: float) -> dict:
    query = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "current": CURRENT_VARIABLES,
            "timeformat": "unixtime",
        }
    )

    try:
        with urlopen(f"{OPEN_METEO_AIR_QUALITY_URL}?{query}", timeout=10) as response:
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
            result = get_current_air_quality(district["latitude"], district["longitude"])
        except SystemExit as error:
            failures += 1
            print(f"Skipped {district['name']}: {error}")
            continue

        observed_at = datetime.fromtimestamp(result["current"]["time"], UTC).isoformat()
        print(
            f"Collected modeled air quality for {district['name']} at "
            f"{observed_at}: US AQI {result['current']['us_aqi']}"
        )
        if save_open_meteo_air_quality_observation(
            result,
            district["name"],
            latitude=district["latitude"],
            longitude=district["longitude"],
        ):
            print("Saved or refreshed modeled air-quality observation in PostgreSQL")

    if failures:
        raise SystemExit(f"Air-quality collection finished with {failures} failed district(s)")


if __name__ == "__main__":
    main()
