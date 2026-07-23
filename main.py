import json
import os
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from dotenv import load_dotenv

from database import save_iqair_observation
load_dotenv()


IQAIR_CITY_URL = "https://api.airvisual.com/v2/city"


def main():
    api_key = os.environ.get("IQAIR_API_KEY")
    if not api_key:
        raise SystemExit("IQAIR_API_KEY is not set")

    query = urlencode(
        {
            "city": "Hanoi",
            "state": "Ha Noi",
            "country": "Vietnam",
            "key": api_key,
        }
    )

    try:
        with urlopen(f"{IQAIR_CITY_URL}?{query}", timeout=10) as response:
            result = json.load(response)
    except HTTPError as error:
        message = error.read().decode("utf-8", errors="replace")
        raise SystemExit(f"IQAir returned HTTP {error.code}: {message}") from None
    except URLError as error:
        raise SystemExit(f"Could not reach IQAir: {error.reason}") from None

    print(json.dumps(result, indent=2))

    if save_iqair_observation(result):
        print("Saved observation to PostgreSQL")
    else:
        print("Observation already exists; nothing new was saved")


if __name__ == "__main__":
    main()
