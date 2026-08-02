"""Collect recent NASA FIRMS VIIRS thermal detections around Hanoi.

These are satellite thermal anomalies, not confirmed fires or proof that a
detected source caused district pollution. Both VIIRS S-NPP and NOAA-20 feeds
are stored so the agent can look for recent, nearby, upwind context.
"""

import csv
import io
import os
from datetime import UTC, datetime
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from dotenv import load_dotenv

from database import save_firms_collection_run, save_firms_fire_observation


load_dotenv()

FIRMS_API_URL = "https://firms.modaps.eosdis.nasa.gov/api/area/csv/{key}/{source}/{area}/{days}"
# West, south, east, north: Hanoi and surrounding potential upwind source area.
HANOI_AREA = "105.55,20.75,106.15,21.35"
FIRMS_SOURCES = ("VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT")


def get_firms_detections(map_key: str, source: str, days: int = 3) -> list[dict[str, str]]:
    url = FIRMS_API_URL.format(key=map_key, source=source, area=HANOI_AREA, days=days)
    try:
        with urlopen(url, timeout=25) as response:
            payload = response.read().decode("utf-8-sig")
    except HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"NASA FIRMS returned HTTP {error.code}: {message}") from None
    except URLError as error:
        raise RuntimeError(f"Could not reach NASA FIRMS: {error.reason}") from None
    return list(csv.DictReader(io.StringIO(payload)))


def main() -> None:
    map_key = os.environ.get("NASA_FIRMS_MAP_KEY")
    if not map_key:
        raise SystemExit("NASA_FIRMS_MAP_KEY is not set in .env")

    collected_at = datetime.now(UTC).isoformat()
    saved = 0
    failed_sources = 0
    for source in FIRMS_SOURCES:
        try:
            detections = get_firms_detections(map_key, source)
        except RuntimeError as error:
            save_firms_collection_run(
                source,
                0,
                collected_at,
                status="failed",
                error_message=str(error),
            )
            failed_sources += 1
            print(f"NASA FIRMS {source}: collection failed ({error})")
            continue
        print(f"NASA FIRMS {source}: {len(detections)} recent Hanoi-area thermal detections")
        for detection in detections:
            if save_firms_fire_observation(detection, source, collected_at):
                saved += 1
        # This is intentionally stored even when detections is empty. Otherwise
        # the dashboard cannot distinguish a successful zero-result query from
        # a query that was never run.
        save_firms_collection_run(source, len(detections), collected_at)
    print(f"Saved {saved} new NASA FIRMS VIIRS thermal detections to PostgreSQL")
    if failed_sources:
        raise SystemExit(f"NASA FIRMS collection failed for {failed_sources} feed(s)")


if __name__ == "__main__":
    main()
