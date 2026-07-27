"""Collect real-time traffic flow at representative major roads in Hanoi."""

import json
import os
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from dotenv import load_dotenv

from database import save_tomtom_traffic_observation


load_dotenv()

TOMTOM_FLOW_URL = (
    "https://api.tomtom.com/traffic/services/4/flowSegmentData/absolute/10/json"
)

# One named, high-traffic road point per pilot district. These are traffic
# context points, not a claim that every road in the district has the same flow.
TRAFFIC_LOCATIONS = [
    {"district_name": "Tay Ho", "road_name": "Vo Chi Cong", "latitude": 21.0627, "longitude": 105.8059},
    {"district_name": "Long Bien", "road_name": "Nguyen Van Cu", "latitude": 21.0437, "longitude": 105.8726},
    {"district_name": "Ba Dinh", "road_name": "Kim Ma", "latitude": 21.0315, "longitude": 105.8214},
    {"district_name": "Cau Giay", "road_name": "Xuan Thuy", "latitude": 21.0380, "longitude": 105.7827},
    {"district_name": "Hoan Kiem", "road_name": "Tran Quang Khai", "latitude": 21.0273, "longitude": 105.8586},
    {"district_name": "Dong Da", "road_name": "Tay Son", "latitude": 21.0068, "longitude": 105.8262},
    {"district_name": "Hai Ba Trung", "road_name": "Dai Co Viet", "latitude": 21.0042, "longitude": 105.8505},
    {"district_name": "Thanh Xuan", "road_name": "Nguyen Trai", "latitude": 20.9977, "longitude": 105.8095},
]


def get_traffic_flow(latitude: float, longitude: float, api_key: str) -> dict:
    query = urlencode({"point": f"{latitude},{longitude}", "key": api_key})
    try:
        with urlopen(f"{TOMTOM_FLOW_URL}?{query}", timeout=10) as response:
            return json.load(response)
    except HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"TomTom returned HTTP {error.code}: {message}") from None
    except URLError as error:
        raise RuntimeError(f"Could not reach TomTom: {error.reason}") from None


def congestion_label(current_speed: float, free_flow_speed: float) -> str:
    if free_flow_speed <= 0:
        return "unknown"

    ratio = current_speed / free_flow_speed
    if ratio >= 0.8:
        return "free-flow"
    if ratio >= 0.5:
        return "moderate"
    return "heavy"


def main() -> None:
    api_key = os.environ.get("TOMTOM_API_KEY")
    if not api_key:
        raise SystemExit("TOMTOM_API_KEY is not set in .env")

    failures = 0
    observed_at = datetime.now(UTC).isoformat()

    for location in TRAFFIC_LOCATIONS:
        try:
            result = get_traffic_flow(
                location["latitude"],
                location["longitude"],
                api_key,
            )
        except RuntimeError as error:
            failures += 1
            print(f"Skipped {location['district_name']}: {error}")
            continue

        flow = result["flowSegmentData"]
        label = congestion_label(flow["currentSpeed"], flow["freeFlowSpeed"])
        print(
            f"Collected TomTom traffic for {location['district_name']} — "
            f"{location['road_name']}: {flow['currentSpeed']} / "
            f"{flow['freeFlowSpeed']} km/h ({label})"
        )
        if save_tomtom_traffic_observation(
            result,
            location["district_name"],
            location["road_name"],
            location["latitude"],
            location["longitude"],
            observed_at,
        ):
            print("Saved traffic observation to PostgreSQL")

    if failures:
        raise SystemExit(f"Traffic collection finished with {failures} failed district(s)")


if __name__ == "__main__":
    main()
