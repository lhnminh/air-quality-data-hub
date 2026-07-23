from api import app


def test_vercel_fastapi_entrypoint_exists():
    paths = {route.path for route in app.routes}

    assert "/api/health" in paths
    assert "/api/observations" in paths
