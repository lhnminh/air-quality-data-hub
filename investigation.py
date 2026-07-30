"""Create evidence-bounded district reports with the Gemini API."""

import json
import os
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


def _fallback_report(context: dict[str, Any]) -> dict[str, Any]:
    """Return the verified evidence if Gemini is unavailable or malformed."""
    district = context["district_name"]
    metrics = []

    if context.get("district_us_aqi") is not None:
        metrics.append(
            {
                "label": "Modelled district US AQI",
                "value": str(context["district_us_aqi"]),
                "source": "Open-Meteo CAMS model",
            }
        )
    if context.get("district_pm2_5_ug_m3") is not None:
        metrics.append(
            {
                "label": "Modelled PM2.5",
                "value": f"{context['district_pm2_5_ug_m3']} µg/m³",
                "source": "Open-Meteo CAMS model",
            }
        )
    if context.get("city_aqi_us") is not None:
        metrics.append(
            {
                "label": "Hanoi city-wide US AQI",
                "value": str(context["city_aqi_us"]),
                "source": "IQAir",
            }
        )
    if context.get("traffic_current_speed_kmh") is not None:
        metrics.append(
            {
                "label": f"Traffic speed near {context.get('traffic_road_name', district)}",
                "value": (
                    f"{context['traffic_current_speed_kmh']} / "
                    f"{context['traffic_free_flow_speed_kmh']} km/h"
                ),
                "source": "TomTom Traffic Flow",
            }
        )

    return {
        "title": f"Air-quality evidence — {district}",
        "summary": (
            "This is a factual data summary. Gemini was unavailable, so no "
            "AI interpretation was added."
        ),
        "numeric_summary": metrics,
        "potential_causes": [
            {
                "label": "Cause not determined",
                "detail": "CAMS estimates, weather, and traffic provide context but do not prove a pollution source.",
            }
        ],
        "data_quality": "CAMS values are regional atmospheric-model estimates, not local ground-sensor measurements.",
    }


def _extract_text(response: dict[str, Any]) -> str:
    candidates = response.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini returned no response candidates")

    parts = candidates[0].get("content", {}).get("parts", [])
    text = "".join(part.get("text", "") for part in parts)
    if not text:
        raise ValueError("Gemini returned an empty response")
    return text


def _validated_report(value: Any, context: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("Gemini did not return a JSON object")

    required_text = ("title", "summary", "data_quality")
    if not all(isinstance(value.get(field), str) for field in required_text):
        raise ValueError("Gemini report is missing required text fields")
    selected_fact_ids = value.get("selected_fact_ids", [])
    if not isinstance(selected_fact_ids, list) or not all(
        isinstance(fact_id, str) for fact_id in selected_fact_ids
    ):
        selected_fact_ids = []
    if not isinstance(value.get("potential_causes"), list):
        raise ValueError("Gemini report is missing potential_causes")

    causes = [
        {"label": cause["label"], "detail": cause["detail"]}
        for cause in value["potential_causes"]
        if isinstance(cause, dict)
        and all(isinstance(cause.get(field), str) for field in ("label", "detail"))
    ]

    # Keep the report schema bounded even if the model adds extra properties.
    return {
        "title": value["title"],
        "summary": value["summary"],
        # The agent selects fact IDs; agent.py maps them to trusted values and
        # sources from the database. Never render Gemini-generated numeric claims.
        "selected_fact_ids": selected_fact_ids[:8],
        "numeric_summary": [],
        "potential_causes": causes,
        "data_quality": value["data_quality"],
    }


def generate_district_report(context: dict[str, Any], prompt: str) -> dict[str, Any]:
    """Ask Gemini to interpret only supplied database evidence."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in .env")

    model = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
    evidence = json.dumps(context, default=str, ensure_ascii=False)
    instructions = """
You are AirTrace, an air-quality decision-support assistant for Hanoi.
Use ONLY the evidence JSON provided by the application. Do not invent readings,
sources, history, or causal claims. CAMS is a regional atmospheric model, not a
ground sensor. Traffic and weather are context only, not proof of cause.

Return valid JSON only, with this exact shape:
{
  "title": "short report title",
  "summary": "2-4 factual sentences",
  "numeric_summary": [{"label": "string", "value": "string", "source": "string"}],
  "potential_causes": [{"label": "string", "detail": "string"}],
  "data_quality": "one concise uncertainty/freshness statement"
}
Include available district CAMS AQI/PM2.5, city IQAir, weather, and traffic in
numeric_summary. If evidence is missing, say so. Use cautious terms such as
"possible context" and "not determined" instead of asserting a cause.
""".strip()
    payload = {
        "systemInstruction": {"parts": [{"text": instructions}]},
        "contents": [
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            f"User request: {prompt}\n\n"
                            f"Evidence JSON:\n{evidence}"
                        )
                    }
                ],
            }
        ],
        "generationConfig": {
            "temperature": 0.2,
            "maxOutputTokens": 900,
            "responseMimeType": "application/json",
        },
    }
    url = f"{GEMINI_API_BASE}/{quote(model, safe='.-')}:generateContent"
    request = Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "x-goog-api-key": api_key,
        },
        method="POST",
    )

    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
        return _validated_report(json.loads(_extract_text(result)), context)
    except (HTTPError, URLError, TimeoutError, ValueError):
        report = _fallback_report(context)
        report["ai_status"] = (
            "Gemini did not return a usable report, so AirTrace is showing "
            "the verified database evidence instead."
        )
        return report
