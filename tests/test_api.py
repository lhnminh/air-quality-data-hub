from api import _comparison_district_from_prompt, app


def test_vercel_fastapi_entrypoint_exists():
    paths = {route.path for route in app.routes}

    assert "/api/health" in paths
    assert "/api/observations" in paths
    assert "/api/weather" in paths
    assert "/api/modeled-air-quality" in paths
    assert "/api/city-air-quality-history" in paths
    assert "/api/district-air-quality-history" in paths
    assert "/api/traffic" in paths
    assert "/api/districts" in paths
    assert "/api/investigate" in paths


def test_manual_comparison_prompt_resolves_one_named_pilot_district():
    assert (
        _comparison_district_from_prompt(
            "Compare Hoan Kiem air quality with Tay Ho", "Hoan Kiem"
        )
        == "Tay Ho"
    )
    assert _comparison_district_from_prompt("Inspect Hoan Kiem air quality", "Hoan Kiem") is None
    assert (
        _comparison_district_from_prompt(
            "Compare Hoan Kiem, Tay Ho, and Ba Dinh", "Hoan Kiem"
        )
        is None
    )
