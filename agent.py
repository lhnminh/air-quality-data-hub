"""Bounded Gemini investigation agent with DataHub and Neon tools."""

import json
import os
from statistics import median
from typing import Any, Callable
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from datahub_mcp import inspect_airtrace_catalog, save_investigation_document
from database import (
    get_district_history,
    get_district_investigation_context,
    save_investigation,
)
from investigation import _fallback_report, _validated_report


GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"


TOOL_DECLARATIONS = [
    {
        "name": "get_datahub_context",
        "description": "Read AirTrace dataset metadata, lineage, and catalog context through DataHub MCP.",
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "get_district_evidence",
        "description": "Read the latest bounded CAMS, IQAir, weather, and TomTom evidence for one Hanoi pilot district from Neon.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"district_name": {"type": "STRING"}},
            "required": ["district_name"],
        },
    },
    {
        "name": "get_district_history",
        "description": "Read up to 24 recent CAMS district observations from Neon when a trend comparison is useful.",
        "parameters": {
            "type": "OBJECT",
            "properties": {"district_name": {"type": "STRING"}},
            "required": ["district_name"],
        },
    },
    {
        "name": "evaluate_district_hypotheses",
        "description": (
            "Run AirTrace's transparent, deterministic evidence assessment for the selected "
            "district. It ranks traffic context, stagnant-weather accumulation, and unknown "
            "cause using bounded Neon evidence. It never claims a proven source."
        ),
        "parameters": {"type": "OBJECT", "properties": {}},
    },
    {
        "name": "compare_district_evidence",
        "description": (
            "Compare the bounded CAMS, IQAir, weather, and TomTom evidence for "
            "the selected district and one explicitly requested Hanoi pilot district."
        ),
        "parameters": {
            "type": "OBJECT",
            "properties": {
                "district_name": {"type": "STRING"},
                "comparison_district_name": {"type": "STRING"},
            },
            "required": ["district_name", "comparison_district_name"],
        },
    },
]


def _tools_for_request(comparison_district_name: str | None) -> list[dict[str, Any]]:
    """Avoid offering the single-district history tool during a comparison.

    The comparison tool already retrieves history for both districts. Keeping the
    narrower history tool out of that request prevents Gemini from accidentally
    asking it for the comparison district and receiving a safety rejection.
    """
    if not comparison_district_name:
        return TOOL_DECLARATIONS
    return [
        declaration
        for declaration in TOOL_DECLARATIONS
        if declaration["name"] != "get_district_history"
    ]


def _gemini_request(payload: dict[str, Any]) -> dict[str, Any]:
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set in .env")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite")
    request = Request(
        f"{GEMINI_API_BASE}/{quote(model, safe='.-')}:generateContent",
        data=json.dumps(payload, default=str).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": api_key},
        method="POST",
    )
    with urlopen(request, timeout=40) as response:
        return json.load(response)


def _candidate_content(response: dict[str, Any]) -> dict[str, Any]:
    candidates = response.get("candidates", [])
    if not candidates:
        raise ValueError("Gemini returned no response candidates")
    content = candidates[0].get("content")
    if not isinstance(content, dict):
        raise ValueError("Gemini returned no content")
    return content


def _function_calls(content: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        part["functionCall"]
        for part in content.get("parts", [])
        if isinstance(part, dict) and isinstance(part.get("functionCall"), dict)
    ]


def _text(content: dict[str, Any]) -> str:
    return "".join(
        part.get("text", "")
        for part in content.get("parts", [])
        if isinstance(part, dict)
    )


def _tool_result(
    tool_name: str,
    arguments: dict[str, Any],
    district_name: str,
    comparison_district_name: str | None = None,
) -> dict[str, Any]:
    if tool_name == "compare_district_evidence":
        requested_district = arguments.get("district_name", district_name)
        requested_comparison = arguments.get("comparison_district_name")
        if (
            not comparison_district_name
            or requested_district != district_name
            or requested_comparison != comparison_district_name
        ):
            return {
                "status": "rejected",
                "summary": "Comparisons are limited to the two districts chosen by the user.",
            }
        primary = get_district_investigation_context(district_name)
        comparison = get_district_investigation_context(comparison_district_name)
        return {
            "status": "connected" if primary and comparison else "missing",
            "primary_evidence": primary or {},
            "comparison_evidence": comparison or {},
            "primary_history": get_district_history(district_name),
            "comparison_history": get_district_history(comparison_district_name),
            "summary": (
                f"Retrieved bounded CAMS, IQAir, weather, TomTom, and recent model-history "
                f"evidence for {district_name} and {comparison_district_name}."
            ),
        }
    requested_district = arguments.get("district_name", district_name)
    if requested_district != district_name:
        return {"status": "rejected", "summary": "Only the selected district may be queried."}
    if tool_name == "get_datahub_context":
        return inspect_airtrace_catalog()
    if tool_name == "get_district_evidence":
        context = get_district_investigation_context(district_name)
        return {
            "status": "connected" if context else "missing",
            "evidence": context or {},
        }
    if tool_name == "get_district_history":
        return {"status": "connected", "history": get_district_history(district_name)}
    if tool_name == "evaluate_district_hypotheses":
        context = get_district_investigation_context(district_name) or {}
        history = get_district_history(district_name)
        return {
            "status": "connected" if context else "missing",
            "assessment": _evaluate_district_hypotheses(context, history),
        }
    return {"status": "rejected", "summary": "Tool is not on the AirTrace allowlist."}


def _trace_item(tool_name: str, result: dict[str, Any]) -> dict[str, Any]:
    status = result.get("status", "connected")
    summary = result.get("summary") or (
        "Retrieved bounded evidence from Neon."
        if status == "connected"
        else "Tool did not return evidence."
    )
    return {
        "tool_name": tool_name,
        "status": status,
        "summary": summary,
        "evidence": result,
    }


def _as_number(value: Any) -> float | None:
    return float(value) if isinstance(value, (float, int)) else None


def _relative_to_history(current: Any, history: list[dict[str, Any]], field: str) -> float | None:
    current_value = _as_number(current)
    values = [_as_number(row.get(field)) for row in history]
    usable = [value for value in values if value is not None]
    if current_value is None or not usable:
        return None
    baseline = median(usable)
    return current_value / baseline if baseline else None


def _evaluate_district_hypotheses(
    context: dict[str, Any], history: list[dict[str, Any]]
) -> dict[str, Any]:
    """Rank hypotheses with transparent rules before Gemini explains them."""
    if not context:
        return {"hypotheses": [], "limitations": ["No district evidence is available."]}

    pm_ratio = _relative_to_history(
        context.get("district_pm2_5_ug_m3"), history, "pm2_5_ug_m3"
    )
    no2_ratio = _relative_to_history(context.get("district_no2_ug_m3"), history, "nitrogen_dioxide_ug_m3")
    congestion = _as_number(context.get("traffic_congestion_percent"))
    wind = _as_number(context.get("wind_speed_kmh"))
    humidity = _as_number(context.get("relative_humidity_percent"))

    traffic_score = 10
    traffic_evidence: list[str] = []
    traffic_against: list[str] = []
    if congestion is None:
        traffic_against.append("No current TomTom congestion value is available.")
    elif congestion >= 50:
        traffic_score += 30
        traffic_evidence.append(f"TomTom congestion is {congestion:.0f}% on the representative road.")
    else:
        traffic_against.append(f"TomTom congestion is only {congestion:.0f}% on the representative road.")
    if no2_ratio is not None and no2_ratio >= 1.2:
        traffic_score += 20
        traffic_evidence.append("Modelled NO₂ is at least 20% above the recent district median.")
    elif no2_ratio is not None:
        traffic_against.append("Modelled NO₂ is not clearly above the recent district median.")

    accumulation_score = 10
    accumulation_evidence: list[str] = []
    accumulation_against: list[str] = []
    if pm_ratio is not None and pm_ratio >= 1.2:
        accumulation_score += 30
        accumulation_evidence.append("Modelled PM2.5 is at least 20% above the recent district median.")
    elif pm_ratio is not None:
        accumulation_against.append("Modelled PM2.5 is not clearly above the recent district median.")
    if wind is not None and wind <= 5:
        accumulation_score += 25
        accumulation_evidence.append(f"Wind is low at {wind:.1f} km/h, which can limit dispersion.")
    elif wind is not None:
        accumulation_against.append(f"Wind is {wind:.1f} km/h, so strong stagnation is less supported.")
    if humidity is not None and humidity >= 85:
        accumulation_score += 10
        accumulation_evidence.append(f"Humidity is high at {humidity:.0f}%.")

    unknown_score = 30
    if not history:
        unknown_score += 30
    if congestion is None:
        unknown_score += 10
    if wind is None:
        unknown_score += 10

    hypotheses = [
        {
            "label": "Traffic contribution",
            "score": min(traffic_score, 100),
            "supporting_evidence": traffic_evidence,
            "contradicting_evidence": traffic_against,
        },
        {
            "label": "Stagnant-weather accumulation or regional transport",
            "score": min(accumulation_score, 100),
            "supporting_evidence": accumulation_evidence,
            "contradicting_evidence": accumulation_against,
        },
        {
            "label": "Cause remains uncertain",
            "score": min(unknown_score, 100),
            "supporting_evidence": ["AirTrace has no local source-attribution sensor or fire feed."],
            "contradicting_evidence": [],
        },
    ]
    return {
        "method": "Transparent heuristic scores (0–100), not probabilities or proof.",
        "hypotheses": sorted(hypotheses, key=lambda item: item["score"], reverse=True),
        "limitations": [
            "CAMS is a regional model estimate, not a local sensor.",
            "TomTom represents one road point and cannot prove a pollution source.",
        ],
    }


def _value(value: Any, suffix: str = "") -> str:
    if value is None:
        return "Not available"
    return f"{value}{suffix}"


def _fact_candidates(context: dict[str, Any]) -> dict[str, dict[str, str]]:
    """Offer Gemini real, source-labelled facts; it may choose but cannot invent one."""
    district = context["district_name"]
    traffic_road = context.get("traffic_road_name") or district
    traffic_speed = context.get("traffic_current_speed_kmh")
    free_flow_speed = context.get("traffic_free_flow_speed_kmh")
    traffic_value = (
        f"{traffic_speed} km/h (free flow {free_flow_speed} km/h)"
        if traffic_speed is not None and free_flow_speed is not None
        else "No current reading"
    )
    candidates = {
        "district_aqi": {
            "label": f"{district} modelled US AQI",
            "value": _value(context.get("district_us_aqi")),
            "source": "Open-Meteo CAMS model estimate",
        },
        "district_pm25": {
            "label": f"{district} modelled PM2.5",
            "value": _value(context.get("district_pm2_5_ug_m3"), " µg/m³"),
            "source": "Open-Meteo CAMS model estimate",
        },
        "district_pm10": {
            "label": f"{district} modelled PM10",
            "value": _value(context.get("district_pm10_ug_m3"), " µg/m³"),
            "source": "Open-Meteo CAMS model estimate",
        },
        "district_no2": {
            "label": f"{district} modelled NO₂",
            "value": _value(context.get("district_no2_ug_m3"), " µg/m³"),
            "source": "Open-Meteo CAMS model estimate",
        },
        "district_ozone": {
            "label": f"{district} modelled O₃",
            "value": _value(context.get("district_ozone_ug_m3"), " µg/m³"),
            "source": "Open-Meteo CAMS model estimate",
        },
        "city_aqi": {
            "label": "Hanoi city-wide US AQI",
            "value": _value(context.get("city_aqi_us")),
            "source": "IQAir city-wide feed",
        },
        "wind": {
            "label": f"Wind in {district}",
            "value": (
                f"{_value(context.get('wind_speed_kmh'), ' km/h')}"
                + (
                    f" from {context['wind_direction_degrees']}°"
                    if context.get("wind_direction_degrees") is not None
                    else ""
                )
            ),
            "source": "Open-Meteo weather model",
        },
        "humidity": {
            "label": f"Humidity in {district}",
            "value": _value(context.get("relative_humidity_percent"), "%"),
            "source": "Open-Meteo weather model",
        },
        "rain": {
            "label": f"Precipitation in {district}",
            "value": _value(context.get("precipitation_mm"), " mm"),
            "source": "Open-Meteo weather model",
        },
        "traffic_speed": {
            "label": f"Traffic on {traffic_road}",
            "value": traffic_value,
            "source": "TomTom Traffic Flow",
        },
        "traffic_congestion": {
            "label": f"Traffic congestion on {traffic_road}",
            "value": _value(context.get("traffic_congestion_percent"), "%"),
            "source": "TomTom Traffic Flow",
        },
    }
    return candidates


def _default_fact_ids(candidates: dict[str, dict[str, str]]) -> list[str]:
    """Use a useful, honest first report if Gemini cannot make a valid selection."""
    preferred = [
        "district_aqi", "district_pm25", "city_aqi", "wind", "humidity", "traffic_speed",
    ]
    return [fact_id for fact_id in preferred if fact_id in candidates]


def _verified_numeric_summary(
    context: dict[str, Any], selected_fact_ids: list[str] | None = None
) -> list[dict[str, str]]:
    """Accept Gemini's relevance choices while preserving source-controlled values."""
    candidates = _fact_candidates(context)
    requested = selected_fact_ids or _default_fact_ids(candidates)
    chosen = []
    # These three facts are required for a meaningful district comparison;
    # Gemini chooses the remaining contextual facts by relevance.
    required_fact_ids = ("district_aqi", "district_pm25", "traffic_speed")
    for fact_id in (*required_fact_ids, *requested):
        if fact_id in candidates and fact_id not in {item["id"] for item in chosen}:
            chosen.append({"id": fact_id, **candidates[fact_id]})
        if len(chosen) == 8:
            break
    return [{key: value for key, value in fact.items() if key != "id"} for fact in chosen]


def _apply_verified_facts(
    report: dict[str, Any],
    context: dict[str, Any],
    datahub_context: dict[str, Any] | None = None,
    history: list[dict[str, Any]] | None = None,
) -> None:
    """Keep AI relevance choices, but make every displayed fact traceable and honest."""
    selected_fact_ids = report.pop("selected_fact_ids", None)
    report["numeric_summary"] = _verified_numeric_summary(context, selected_fact_ids)
    datahub_note = "DataHub was unavailable for this inspection."
    if datahub_context and datahub_context.get("status") == "connected":
        datahub_note = datahub_context.get("summary", "DataHub source contracts were verified.")
    report["data_quality"] = (
        "District AQI and pollutant values are Open-Meteo CAMS regional model "
        "estimates, not ground-sensor readings. IQAir is city-wide. Traffic is "
        "one representative TomTom road-flow point and provides context only. "
        + datahub_note
    )
    assessment = _evaluate_district_hypotheses(context, history or [])
    report["hypothesis_ranking"] = assessment["hypotheses"]
    report["assessment_method"] = assessment.get("method")


def _prepend_inspection_evidence_lead(
    report: dict[str, Any],
    context: dict[str, Any],
    history: list[dict[str, Any]],
) -> None:
    """Add one verified AQI/PM2.5 lead without relying on Gemini's wording."""
    aqi = _as_number(context.get("district_us_aqi"))
    pm25 = _as_number(context.get("district_pm2_5_ug_m3"))
    if aqi is None and pm25 is None:
        return
    historical_aqi = [_as_number(row.get("us_aqi")) for row in history]
    historical_pm25 = [_as_number(row.get("pm2_5_ug_m3")) for row in history]
    usable_aqi_history = [value for value in historical_aqi if value is not None]
    usable_history = [value for value in historical_pm25 if value is not None]
    lead_parts: list[str] = []
    if aqi is not None and usable_aqi_history:
        recent_aqi_median = median(usable_aqi_history)
        aqi_change_percent = (
            (aqi - recent_aqi_median) / recent_aqi_median * 100 if recent_aqi_median else 0
        )
        if aqi_change_percent >= 20:
            relation = f"elevated at {aqi:.0f}, {aqi_change_percent:.0f}% above"
        elif aqi_change_percent <= -20:
            relation = f"{aqi:.0f}, {abs(aqi_change_percent):.0f}% below"
        else:
            relation = f"{aqi:.0f}, close to"
        lead_parts.append(
            f"The current CAMS-modelled US AQI is {relation} the recent district median of "
            f"{recent_aqi_median:.0f}; higher AQI values indicate worse modelled air quality."
        )
    elif aqi is not None:
        lead_parts.append(
            f"The current CAMS-modelled US AQI is {aqi:.0f}; higher AQI values indicate worse "
            "modelled air quality, but recent district history is unavailable for a trend comparison."
        )
    if pm25 is not None and usable_history:
        recent_median = median(usable_history)
        change_percent = ((pm25 - recent_median) / recent_median * 100) if recent_median else 0
        if change_percent >= 20:
            lead_parts.append(
                f"Modelled PM2.5 is elevated at {pm25:.1f} µg/m³, {change_percent:.0f}% above "
                f"the recent district median of {recent_median:.1f} µg/m³."
            )
        elif change_percent <= -20:
            lead_parts.append(
                f"Modelled PM2.5 is {pm25:.1f} µg/m³, {abs(change_percent):.0f}% below "
                f"the recent district median of {recent_median:.1f} µg/m³."
            )
        else:
            lead_parts.append(
                f"Modelled PM2.5 is {pm25:.1f} µg/m³, close to the recent district "
                f"median of {recent_median:.1f} µg/m³."
            )
    elif pm25 is not None:
        lead_parts.append(
            f"Modelled PM2.5 is {pm25:.1f} µg/m³; recent district history is unavailable "
            "for a trend comparison."
        )
    lead = " ".join(lead_parts)
    summary = str(report.get("summary", "")).strip()
    report["summary"] = f"{lead} {summary}".strip()


def _comparison_facts(context: dict[str, Any]) -> list[dict[str, str]]:
    """Return a compact, source-controlled counterpart snapshot for comparisons."""
    district = context.get("district_name", "Comparison district")
    road = context.get("traffic_road_name") or district
    speed = context.get("traffic_current_speed_kmh")
    free_flow = context.get("traffic_free_flow_speed_kmh")
    speed_value = (
        f"{speed} km/h (free flow {free_flow} km/h)"
        if speed is not None and free_flow is not None
        else "No current reading"
    )
    return [
        {
            "label": f"{district} modelled US AQI",
            "value": _value(context.get("district_us_aqi")),
            "source": "Open-Meteo CAMS model estimate",
        },
        {
            "label": f"{district} modelled PM2.5",
            "value": _value(context.get("district_pm2_5_ug_m3"), " µg/m³"),
            "source": "Open-Meteo CAMS model estimate",
        },
        {
            "label": f"Wind in {district}",
            "value": _value(context.get("wind_speed_kmh"), " km/h"),
            "source": "Open-Meteo weather model",
        },
        {
            "label": f"Traffic on {road}",
            "value": speed_value,
            "source": "TomTom Traffic Flow",
        },
    ]


def _apply_comparison(
    report: dict[str, Any],
    primary: dict[str, Any],
    comparison: dict[str, Any],
) -> None:
    """Make a comparison explicit without letting Gemini invent either side's values."""
    first = primary.get("district_name", "Selected district")
    second = comparison.get("district_name", "Comparison district")
    first_aqi = _as_number(primary.get("district_us_aqi"))
    second_aqi = _as_number(comparison.get("district_us_aqi"))
    if first_aqi is not None and second_aqi is not None:
        difference = abs(first_aqi - second_aqi)
        if difference == 0:
            comparison_sentence = (
                f"{first} and {second} have the same current CAMS-modelled AQI "
                f"of {first_aqi:.0f}."
            )
        else:
            higher = first if first_aqi > second_aqi else second
            comparison_sentence = (
                f"{higher} has the higher current CAMS-modelled AQI; the difference is "
                f"{difference:.0f} AQI points."
            )
    else:
        comparison_sentence = "One or both districts are missing a current modelled AQI."
    report["title"] = f"Air-quality comparison — {first} vs {second}"
    report["summary"] = f"{report['summary']} {comparison_sentence}"
    # Keep matching facts beside one another in the two-column UI: AQI versus
    # AQI, then PM2.5 versus PM2.5, wind versus wind, and traffic versus traffic.
    # This is clearer than grouping all four facts by district.
    primary_facts = _comparison_facts(primary)
    comparison_facts = _comparison_facts(comparison)
    report["numeric_summary"] = [
        fact
        for pair in zip(primary_facts, comparison_facts)
        for fact in pair
    ]
    report["comparison_note"] = (
        "Both district values are CAMS model estimates. IQAir remains a separate, "
        "city-wide reference; weather and one TomTom road point per district provide context only."
    )
    report["comparison_mode"] = True


def _markdown_cell(value: Any) -> str:
    """Keep report values readable inside a Markdown table cell."""
    return str(value).replace("|", "\\|").replace("\n", "<br>")


def _format_investigation_document(
    district_name: str,
    prompt: str,
    report: dict[str, Any],
) -> str:
    """Turn a structured investigation report into readable DataHub Markdown."""
    title = report.get("title") or f"AirTrace investigation — {district_name}"
    lines = [
        f"# {title}",
        "",
        f"**District:** {district_name}",
        "",
        "**Investigation prompt:**",
        "",
        f"> {prompt.replace(chr(10), chr(10) + '> ')}",
        "",
        "## Summary",
        "",
        str(report.get("summary") or "No summary was generated."),
    ]

    metrics = report.get("numeric_summary")
    if isinstance(metrics, list) and metrics:
        lines.extend(
            [
                "",
                "## Key metrics",
                "",
                "| Metric | Value | Source |",
                "| --- | --- | --- |",
            ]
        )
        for metric in metrics:
            if not isinstance(metric, dict):
                continue
            lines.append(
                "| "
                f"{_markdown_cell(metric.get('label', 'Metric'))} | "
                f"{_markdown_cell(metric.get('value', 'Unavailable'))} | "
                f"{_markdown_cell(metric.get('source', 'Unspecified'))} |"
            )

    causes = report.get("potential_causes")
    if isinstance(causes, list) and causes:
        lines.extend(["", "## Potential causes"])
        for index, cause in enumerate(causes, start=1):
            if not isinstance(cause, dict):
                continue
            lines.extend(
                [
                    "",
                    f"### {index}. {cause.get('label', 'Unspecified cause')}",
                    "",
                    str(cause.get("detail") or "No details provided."),
                ]
            )

    hypotheses = report.get("hypothesis_ranking")
    if isinstance(hypotheses, list) and hypotheses:
        lines.extend(["", "## Ranked hypotheses"])
        for index, hypothesis in enumerate(hypotheses, start=1):
            if not isinstance(hypothesis, dict):
                continue
            label = hypothesis.get("label", "Unspecified hypothesis")
            score = hypothesis.get("score", "—")
            lines.extend(["", f"### {index}. {label} — {score}/100"])
            for heading, key in (
                ("Supporting evidence", "supporting_evidence"),
                ("Contradicting evidence", "contradicting_evidence"),
            ):
                evidence = hypothesis.get(key)
                lines.extend(["", f"**{heading}:**"])
                if isinstance(evidence, list) and evidence:
                    lines.extend(f"- {item}" for item in evidence)
                else:
                    lines.append("- None recorded.")

    if report.get("data_quality"):
        lines.extend(
            ["", "## Data quality and limitations", "", str(report["data_quality"])]
        )
    if report.get("comparison_note"):
        lines.extend(["", "## Comparison note", "", str(report["comparison_note"])])
    if report.get("assessment_method"):
        lines.extend(["", "## Assessment method", "", str(report["assessment_method"])])

    action = report.get("recommended_action")
    if isinstance(action, dict):
        approval = "Required" if action.get("requires_human_approval") else "Not required"
        action_type = str(action.get("type", "unspecified")).replace("_", " ").title()
        lines.extend(
            [
                "",
                "## Recommended action",
                "",
                str(action.get("description") or "No action was recommended."),
                "",
                f"- **Action type:** {action_type}",
                f"- **Human approval:** {approval}",
            ]
        )

    return "\n".join(lines).strip() + "\n"


def _fallback_agent_result(
    district_name: str,
    prompt: str,
    tool_trace: list[dict[str, Any]],
    datahub_context: dict[str, Any],
    comparison_district_name: str | None = None,
) -> dict[str, Any]:
    evidence = get_district_investigation_context(district_name) or {"district_name": district_name}
    report = _fallback_report(evidence)
    _apply_verified_facts(report, evidence, datahub_context, get_district_history(district_name))
    if comparison_district_name:
        comparison = get_district_investigation_context(comparison_district_name) or {
            "district_name": comparison_district_name
        }
        _apply_comparison(report, evidence, comparison)
    else:
        _prepend_inspection_evidence_lead(
            report, evidence, get_district_history(district_name)
        )
    report["recommended_action"] = {
        "type": "human_review",
        "description": "Review the evidence before any public alert or operational response.",
        "requires_human_approval": True,
    }
    datahub_write = save_investigation_document(
        _format_investigation_document(district_name, prompt, report),
        title=f"AirTrace investigation — {district_name}",
    )
    tool_trace.append(_trace_item("save_investigation_to_datahub", datahub_write))
    saved = save_investigation(
        district_name,
        prompt,
        os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        report,
        datahub_context,
        tool_trace,
    )
    return {"report": report, "tool_trace": tool_trace, "investigation": saved}


def run_district_agent(
    district_name: str,
    prompt: str,
    comparison_district_name: str | None = None,
) -> dict[str, Any]:
    """Let Gemini select bounded tools, then persist a review-only outcome."""
    system_instruction = """
You are the AirTrace investigation agent for Hanoi. You must first inspect
DataHub context and district evidence using available tools. You may inspect
district history and the transparent hypothesis assessment if useful. DataHub
contracts tell you which source is district-level, city-wide, modelled, or only
context; use those distinctions in your explanation. Never query another
district, invent a reading, claim a proven cause, send a public alert, or take
an irreversible action.
After tools return, output JSON only:
{
  "title": "string", "summary": "string",
  "selected_fact_ids": ["one or more allowed fact IDs"],
  "potential_causes": [{"label":"string","detail":"string"}],
  "data_quality": "string",
  "recommended_action": {
    "type":"human_review", "description":"string", "requires_human_approval":true
  }
}
Use cautious wording. CAMS is a model estimate, not a local sensor. Never call
CAMS data a sensor, station, monitor, or measurement from an active district.
After you receive the evidence, select the 4–8 most decision-relevant fact IDs
from the bounded evidence package. The application will display only those real
values and their source labels. Always select district_aqi, district_pm25, and
traffic_speed; use the remaining slots for the strongest contextual evidence.
Never write a value or source label yourself. For each potential cause, include
only evidence that is actually returned by the allowed tools.
""".strip()
    if comparison_district_name:
        system_instruction += (
            "\nThis is a comparison request. You must call compare_district_evidence for "
            f"{district_name} and {comparison_district_name}. Write a short, useful comparison "
            "analysis, not a list of numbers. Explain what the AQI comparison means (a higher "
            "AQI means worse modelled air quality; equal AQIs mean this model does not show a "
            "current difference), what PM2.5 means (fine particle pollution), and whether the "
            "wind and traffic values support a meaningful contextual difference. Lower wind can "
            "limit dispersion; traffic speed compared with free-flow speed describes one road's "
            "flow only. Never treat wind or traffic as proof of a pollution source. If evidence "
            "is the same or too limited, say that plainly. Explain only differences supported by "
            "the bounded evidence. Keep summary to two or three concise sentences; do not repeat "
            "every number because the fact cards show them. In potential_causes, return two or "
            "three short comparison interpretations: one about what the air-quality difference "
            "means, one about whether wind and traffic distinguish the districts, and, when "
            "needed, one explaining why the available evidence cannot identify a pollution source. "
            "These are interpretations without scores, not proof or a source ranking."
        )
    else:
        system_instruction += (
            "\nFor a normal inspection, the application adds the verified AQI-versus-history "
            "and PM2.5 opening itself. Do not repeat current AQI or PM2.5 values in your summary. "
            "Write two concise sentences interpreting only weather, traffic, and uncertainty "
            "without claiming a proven cause. For each "
            "potential cause, include its transparent evidence score and both "
            "supporting and contradicting evidence from evaluate_district_hypotheses. Scores "
            "are not probabilities or proof."
        )
    contents: list[dict[str, Any]] = [
        {
            "role": "user",
            "parts": [
                {
                    "text": (
                        f"{prompt}\nSelected district: {district_name}"
                        + (
                            f"\nComparison district: {comparison_district_name}"
                            if comparison_district_name
                            else ""
                        )
                    )
                }
            ],
        }
    ]
    tool_trace: list[dict[str, Any]] = []
    datahub_context: dict[str, Any] = {}
    available_tools = _tools_for_request(comparison_district_name)
    try:
        for _ in range(3):
            response = _gemini_request(
                {
                    "systemInstruction": {"parts": [{"text": system_instruction}]},
                    "contents": contents,
                    "tools": [{"functionDeclarations": available_tools}],
                    "toolConfig": {"functionCallingConfig": {"mode": "ANY"}},
                    "generationConfig": {"temperature": 0.1, "maxOutputTokens": 700},
                }
            )
            content = _candidate_content(response)
            calls = _function_calls(content)
            if not calls:
                break
            contents.append(content)
            for call in calls:
                tool_name = call.get("name", "")
                result = _tool_result(
                    tool_name,
                    call.get("args", {}),
                    district_name,
                    comparison_district_name,
                )
                trace = _trace_item(tool_name, result)
                tool_trace.append(trace)
                if tool_name == "get_datahub_context":
                    datahub_context = result
                contents.append(
                    {
                        "role": "user",
                        "parts": [
                            {
                                "functionResponse": {
                                    "name": tool_name,
                                    "response": {"result": result},
                                }
                            }
                        ],
                    }
                )

        # These four evidence checks are policy-required: Gemini may explore
        # them itself, but the backend guarantees that every report is grounded
        # in the same bounded, auditable package.
        required_tools = (
            "get_datahub_context",
            "get_district_evidence",
            "evaluate_district_hypotheses",
        )
        if comparison_district_name:
            # compare_district_evidence includes both histories.
            required_tools = (*required_tools, "compare_district_evidence")
        else:
            required_tools = (*required_tools, "get_district_history")
        called_tools = {trace["tool_name"] for trace in tool_trace}
        required_evidence: dict[str, Any] = {}
        for tool_name in required_tools:
            if tool_name in called_tools:
                continue
            arguments = (
                {
                    "district_name": district_name,
                    "comparison_district_name": comparison_district_name,
                }
                if tool_name == "compare_district_evidence"
                else {}
            )
            result = _tool_result(
                tool_name, arguments, district_name, comparison_district_name
            )
            trace = _trace_item(tool_name, result)
            tool_trace.append(trace)
            required_evidence[tool_name] = result
            if tool_name == "get_datahub_context":
                datahub_context = result
        if required_evidence:
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "text": (
                                "Policy-required evidence package collected by AirTrace. "
                                "Use it as the authoritative data for your final JSON:\n"
                                + json.dumps(required_evidence, default=str)
                            )
                        }
                    ],
                }
            )

        fact_context = get_district_investigation_context(district_name) or {
            "district_name": district_name
        }
        contents.append(
            {
                "role": "user",
                "parts": [
                    {
                        "text": (
                            "Source-controlled fact candidates. Select IDs only; do not copy or "
                            "alter their values or source labels:\n"
                            + json.dumps(_fact_candidates(fact_context), default=str)
                        )
                    }
                ],
            }
        )

        final_response = _gemini_request(
            {
                "systemInstruction": {"parts": [{"text": system_instruction}]},
                "contents": contents,
                "generationConfig": {
                    "temperature": 0.1,
                    "maxOutputTokens": 900,
                    "responseMimeType": "application/json",
                },
            }
        )
        report = _validated_report(json.loads(_text(_candidate_content(final_response))), {})
        current_context = get_district_investigation_context(district_name) or {
            "district_name": district_name
        }
        _apply_verified_facts(
            report,
            current_context,
            datahub_context,
            get_district_history(district_name),
        )
        if comparison_district_name:
            comparison_context = get_district_investigation_context(
                comparison_district_name
            ) or {"district_name": comparison_district_name}
            _apply_comparison(report, current_context, comparison_context)
        else:
            _prepend_inspection_evidence_lead(
                report,
                current_context,
                get_district_history(district_name),
            )
        report["recommended_action"] = {
            "type": "human_review",
            "description": "Review the evidence before any public alert or operational response.",
            "requires_human_approval": True,
        }
    except (
        HTTPError,
        URLError,
        TimeoutError,
        TypeError,
        ValueError,
        RuntimeError,
        json.JSONDecodeError,
    ):
        if not tool_trace:
            evidence = get_district_investigation_context(district_name) or {}
            tool_trace.append(
                _trace_item("get_district_evidence", {"status": "connected", "evidence": evidence})
            )
        return _fallback_agent_result(
            district_name,
            prompt,
            tool_trace,
            datahub_context,
            comparison_district_name,
        )

    datahub_write = save_investigation_document(
        _format_investigation_document(district_name, prompt, report),
        title=f"AirTrace investigation — {district_name}",
    )
    tool_trace.append(_trace_item("save_investigation_to_datahub", datahub_write))
    saved = save_investigation(
        district_name,
        prompt,
        os.environ.get("GEMINI_MODEL", "gemini-3.1-flash-lite"),
        report,
        datahub_context,
        tool_trace,
    )
    return {"report": report, "tool_trace": tool_trace, "investigation": saved}
