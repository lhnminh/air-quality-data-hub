import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from database import (
    check_database_connection,
    get_city_air_quality_history,
    get_district_air_quality_history,
    get_district_statuses,
    get_district_investigation_context,
    get_recent_modeled_air_quality_observations,
    get_recent_observations,
    get_recent_fire_observations,
    get_recent_traffic_observations,
    get_recent_weather_observations,
)
from districts import DISTRICTS
from agent import run_district_agent

app = FastAPI(title="AerX API")

# The local frontend runs on port 3000. FRONTEND_URL can be changed later
# when the frontend is deployed.
frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class InvestigationRequest(BaseModel):
    district_name: str
    prompt: str = Field(min_length=1, max_length=500)
    comparison_district_name: str | None = Field(default=None, max_length=100)


@app.get("/api/health")
def health_check() -> dict:
    database_connected = check_database_connection()

    return {
        "status": "ok" if database_connected else "error",
        "database": "PostgreSQL",
        "database_connected": database_connected,
    }


@app.get("/api/observations")
def recent_observations(
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    observations = get_recent_observations(limit=limit)
    return {
        "count": len(observations),
        "observations": observations,
    }


@app.get("/api/weather")
def recent_weather_observations(
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    observations = get_recent_weather_observations(limit=limit)
    return {
        "count": len(observations),
        "observations": observations,
    }


@app.get("/api/modeled-air-quality")
def recent_modeled_air_quality_observations(
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    observations = get_recent_modeled_air_quality_observations(limit=limit)
    return {
        "count": len(observations),
        "observations": observations,
    }


@app.get("/api/city-air-quality-history")
def city_air_quality_history(
    city: str = Query(default="Hanoi", min_length=1, max_length=100),
    days: int = Query(default=30, ge=1, le=3660),
) -> dict:
    observations = get_city_air_quality_history(city=city, days=days)
    return {
        "city": city,
        "days": days,
        "count": len(observations),
        "observations": observations,
    }


@app.get("/api/district-air-quality-history")
def district_air_quality_history(
    district_name: str = Query(min_length=1, max_length=100),
    days: int = Query(default=30, ge=1, le=3660),
) -> dict:
    canonical_names = {
        district["name"].casefold(): district["name"] for district in DISTRICTS
    }
    canonical_name = canonical_names.get(district_name.strip().casefold())
    if not canonical_name:
        raise HTTPException(status_code=404, detail="Unknown Hanoi pilot district")

    observations = get_district_air_quality_history(
        district_name=canonical_name,
        days=days,
    )
    return {
        "district_name": canonical_name,
        "days": days,
        "count": len(observations),
        "observations": observations,
    }


@app.get("/api/traffic")
def recent_traffic_observations(
    limit: int = Query(default=20, ge=1, le=100),
) -> dict:
    observations = get_recent_traffic_observations(limit=limit)
    return {
        "count": len(observations),
        "observations": observations,
    }


@app.get("/api/fires")
def recent_fire_observations(
    limit: int = Query(default=100, ge=1, le=500),
) -> dict:
    observations = get_recent_fire_observations(limit=limit)
    return {"count": len(observations), "observations": observations}


@app.get("/api/districts")
def district_statuses() -> dict:
    districts = get_district_statuses()
    return {"count": len(districts), "districts": districts}


@app.post("/api/investigate")
def investigate_district(request: InvestigationRequest) -> dict:
    district_names = {district["name"] for district in DISTRICTS}
    if request.district_name not in district_names:
        raise HTTPException(status_code=404, detail="Unknown Hanoi pilot district")
    if (
        request.comparison_district_name
        and request.comparison_district_name not in district_names
    ):
        raise HTTPException(status_code=404, detail="Unknown comparison district")
    if request.comparison_district_name == request.district_name:
        raise HTTPException(
            status_code=422,
            detail="Choose a different district to compare",
        )

    context = get_district_investigation_context(request.district_name)
    if not context:
        raise HTTPException(
            status_code=404,
            detail="No investigation data is available for this district yet",
        )

    agent_result = run_district_agent(
        request.district_name,
        request.prompt,
        request.comparison_district_name,
    )
    return {
        "district_name": request.district_name,
        "prompt": request.prompt,
        **agent_result,
    }
