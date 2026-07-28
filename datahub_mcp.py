"""Small, optional stdio client for the self-hosted DataHub MCP server."""

import json
import os
import subprocess
import uuid
from typing import Any

from dotenv import load_dotenv


# The API process must read the developer's local configuration before it
# starts the MCP subprocess. Uvicorn does not automatically load .env files.
load_dotenv()


AIRTRACE_DATA_CONTRACTS = {
    "modeled_air_quality_observations": {
        "source_label": "Open-Meteo CAMS model estimate",
        "scope": "district-level regional atmospheric-model estimate, not a ground sensor",
        "required_fields": ["district_name", "observed_at", "us_aqi", "pm2_5_ug_m3"],
    },
    "air_quality_observations": {
        "source_label": "IQAir city-wide feed",
        "scope": "Hanoi city-wide observation, not a district reading",
        "required_fields": ["observed_at", "aqi_us", "main_pollutant"],
    },
    "weather_observations": {
        "source_label": "Open-Meteo weather model",
        "scope": "district weather context; it can support, but not prove, a cause",
        "required_fields": ["district_name", "observed_at", "wind_speed_kmh", "wind_direction_degrees"],
    },
    "traffic_observations": {
        "source_label": "TomTom Traffic Flow",
        "scope": "one representative road-flow point per district; context only",
        "required_fields": ["district_name", "observed_at", "road_name", "congestion_percent"],
    },
}


def _not_configured() -> dict[str, Any]:
    return {
        "status": "not_configured",
        "summary": (
            "DataHub MCP is not configured. Set DATAHUB_GMS_URL and "
            "DATAHUB_GMS_TOKEN to let the agent inspect catalog metadata."
        ),
    }


def _request(process: subprocess.Popen[str], message: dict[str, Any]) -> dict[str, Any]:
    assert process.stdin is not None
    assert process.stdout is not None
    process.stdin.write(json.dumps(message) + "\n")
    process.stdin.flush()
    while line := process.stdout.readline():
        try:
            response = json.loads(line)
        except json.JSONDecodeError:
            continue
        if response.get("id") == message.get("id"):
            if "error" in response:
                raise RuntimeError(response["error"].get("message", "DataHub MCP error"))
            return response.get("result", {})
    raise RuntimeError("DataHub MCP ended before responding")


def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Start the official MCP server and invoke one DataHub tool."""
    gms_url = os.environ.get("DATAHUB_GMS_URL")
    gms_token = os.environ.get("DATAHUB_GMS_TOKEN")
    if not gms_url or not gms_token:
        return _not_configured()

    command = os.environ.get("DATAHUB_MCP_COMMAND", "mcp-server-datahub")
    environment = {
        **os.environ,
        "DATAHUB_GMS_URL": gms_url,
        "DATAHUB_GMS_TOKEN": gms_token,
    }
    try:
        with subprocess.Popen(
            [command],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            env=environment,
        ) as process:
            _request(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": 1,
                    "method": "initialize",
                    "params": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {},
                        "clientInfo": {"name": "airtrace", "version": "0.1.0"},
                    },
                },
            )
            assert process.stdin is not None
            process.stdin.write(
                json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"})
                + "\n"
            )
            process.stdin.flush()
            return _request(
                process,
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": name, "arguments": arguments},
                },
            )
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        return {"status": "unavailable", "summary": f"DataHub MCP unavailable: {error}"}


def _structured_result(result: dict[str, Any]) -> Any:
    """Read structured MCP output, with a text fallback for older servers."""
    structured = result.get("structuredContent", {})
    if isinstance(structured, dict) and "result" in structured:
        return structured["result"]
    for item in result.get("content", []):
        if isinstance(item, dict) and isinstance(item.get("text"), str):
            try:
                return json.loads(item["text"])
            except json.JSONDecodeError:
                continue
    return None


def list_available_tools() -> dict[str, Any]:
    """Return the tools exposed by the configured DataHub MCP server."""
    gms_url = os.environ.get("DATAHUB_GMS_URL")
    gms_token = os.environ.get("DATAHUB_GMS_TOKEN")
    if not gms_url or not gms_token:
        return _not_configured()
    command = os.environ.get("DATAHUB_MCP_COMMAND", "mcp-server-datahub")
    environment = {**os.environ, "DATAHUB_GMS_URL": gms_url, "DATAHUB_GMS_TOKEN": gms_token}
    try:
        with subprocess.Popen(
            [command],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            env=environment,
        ) as process:
            _request(
                process,
                {
                    "jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                               "clientInfo": {"name": "airtrace", "version": "0.1.0"}},
                },
            )
            return _request(process, {"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
    except (OSError, RuntimeError, subprocess.SubprocessError) as error:
        return {"status": "unavailable", "summary": f"DataHub MCP unavailable: {error}"}


def inspect_airtrace_catalog() -> dict[str, Any]:
    """Verify source meaning and required fields against DataHub's live catalog."""
    search = _call_tool(
        "search",
        {
            "query": "/q air_quality_observations OR weather_observations OR "
            "modeled_air_quality_observations OR traffic_observations",
            "filter": "entity_type = dataset AND platform = postgres",
            "num_results": 20,
        },
    )
    if search.get("status") in {"not_configured", "unavailable"}:
        return search

    search_result = _structured_result(search) or {}
    search_rows = search_result.get("searchResults", []) if isinstance(search_result, dict) else []
    urns = [
        row.get("entity", {}).get("urn")
        for row in search_rows
        if row.get("entity", {}).get("properties", {}).get("name") in AIRTRACE_DATA_CONTRACTS
    ]
    urns = [urn for urn in urns if isinstance(urn, str)]
    entities_result = _call_tool("get_entities", {"urns": urns}) if urns else {}
    entities = _structured_result(entities_result) or []
    if isinstance(entities, dict):
        entities = [entities]

    fields_by_table = {
        entity.get("properties", {}).get("name"): {
            field.get("fieldPath")
            for field in entity.get("schemaMetadata", {}).get("fields", [])
            if isinstance(field.get("fieldPath"), str)
        }
        for entity in entities
        if isinstance(entity, dict)
    }
    assets = []
    for table, contract in AIRTRACE_DATA_CONTRACTS.items():
        fields = fields_by_table.get(table, set())
        missing_fields = [field for field in contract["required_fields"] if field not in fields]
        assets.append(
            {
                "table": table,
                "catalogued": bool(fields),
                "required_fields_present": not missing_fields,
                "missing_fields": missing_fields,
                "source_label": contract["source_label"],
                "scope": contract["scope"],
            }
        )

    verified_count = sum(asset["required_fields_present"] for asset in assets)
    return {
        "status": "connected",
        "summary": (
            f"DataHub MCP verified {verified_count}/{len(assets)} AirTrace source "
            "contracts against live PostgreSQL schemas."
        ),
        "assets": assets,
        "catalog_result": json.dumps(assets),
    }


def save_investigation_document(
    document: str, title: str = "AirTrace investigation"
) -> dict[str, Any]:
    """Write a concise, review-only investigation record through DataHub's REST API."""
    if os.environ.get("DATAHUB_MCP_WRITE_ENABLED") != "true":
        return {
            "status": "not_enabled",
            "summary": "DataHub write-back is disabled; the Neon audit record was saved.",
        }
    gms_url = os.environ.get("DATAHUB_GMS_URL")
    gms_token = os.environ.get("DATAHUB_GMS_TOKEN")
    if not gms_url or not gms_token:
        return _not_configured()

    try:
        from datahub.sdk import DataHubClient, Document
    except ImportError:
        return {
            "status": "unavailable",
            "summary": "DataHub SDK is not installed; run `uv sync --extra datahub`.",
        }

    document_id = f"airtrace-investigation-{uuid.uuid4()}"
    document_urn = f"urn:li:document:{document_id}"
    related_assets = [
        "urn:li:dataset:(urn:li:dataPlatform:postgres,"
        f"airtrace-neon.neondb.public.{table},PROD)"
        for table in AIRTRACE_DATA_CONTRACTS
    ]
    try:
        client = DataHubClient(server=gms_url, token=gms_token)
        saved_document = Document.create_document(
            id=document_id,
            title=title,
            text=document,
            subtype="Reference",
            show_in_global_context=True,
            related_assets=related_assets,
            custom_properties={"created_by": "AirTrace investigation agent"},
        )
        # Explicitly emit this aspect even though `True` is DataHub's SDK
        # default. The Documents sidebar in the local OSS UI filters on the
        # persisted setting, while a missing aspect is only treated as true by
        # the API/search layer. Persisting it makes the report discoverable in
        # both places.
        saved_document.show_in_global_search()
        client.entities.upsert(saved_document)
    except Exception as error:  # DataHub is optional; never block a Neon audit record.
        return {"status": "unavailable", "summary": f"DataHub write-back unavailable: {error}"}
    return {
        "status": "saved",
        "summary": "Investigation was written to DataHub Documents through the DataHub REST API.",
        "document_urn": document_urn,
    }
