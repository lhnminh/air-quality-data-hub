import os

from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

from database import check_database_connection, get_recent_observations

app = FastAPI(title="AirTrace API")

# The local frontend runs on port 3000. FRONTEND_URL can be changed later
# when the frontend is deployed.
frontend_url = os.environ.get("FRONTEND_URL", "http://localhost:3000")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_url],
    allow_methods=["GET"],
    allow_headers=["*"],
)


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
