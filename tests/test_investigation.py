import agent
import investigation


def test_fallback_report_uses_only_available_evidence():
    report = investigation._fallback_report(
        {
            "district_name": "Ba Dinh",
            "district_us_aqi": 121,
            "district_pm2_5_ug_m3": 43.2,
            "city_aqi_us": 86,
            "traffic_road_name": "Kim Ma",
            "traffic_current_speed_kmh": 18.0,
            "traffic_free_flow_speed_kmh": 39.0,
        }
    )

    assert report["title"].endswith("Ba Dinh")
    assert len(report["numeric_summary"]) == 4
    assert report["potential_causes"][0]["label"] == "Cause not determined"


def test_validated_report_discards_unstructured_model_items():
    report = investigation._validated_report(
        {
                "title": "Ba Dinh inspection",
                "summary": "A cautious summary.",
                "selected_fact_ids": ["district_aqi", "not-a-real-fact", 23],
            "potential_causes": [
                {"label": "Traffic context", "detail": "Not proof."},
                "not an object",
            ],
            "data_quality": "Modelled data.",
        },
        {"district_name": "Ba Dinh"},
    )

    assert report["numeric_summary"] == []
    assert report["selected_fact_ids"] == []
    assert report["potential_causes"] == [
        {"label": "Traffic context", "detail": "Not proof."}
    ]


def test_verified_facts_always_include_honestly_labelled_traffic():
    report = {
        "selected_fact_ids": [
            "district_aqi",
            "district_pm25",
            "city_aqi",
            "wind",
            "traffic_speed",
        ],
        "numeric_summary": [],
        "data_quality": "unverified",
    }

    agent._apply_verified_facts(
        report,
        {
            "district_name": "Hoan Kiem",
            "district_us_aqi": 159,
            "district_pm2_5_ug_m3": 156.5,
            "city_aqi_us": 97,
            "wind_speed_kmh": 1.6,
            "traffic_road_name": "Tran Quang Khai",
            "traffic_current_speed_kmh": 21.0,
            "traffic_free_flow_speed_kmh": 38.0,
        },
    )

    assert report["numeric_summary"] == [
        {
            "label": "Hoan Kiem modelled US AQI",
            "value": "159",
            "source": "Open-Meteo CAMS model estimate",
        },
        {
            "label": "Hoan Kiem modelled PM2.5",
            "value": "156.5 µg/m³",
            "source": "Open-Meteo CAMS model estimate",
        },
        {
            "label": "Traffic on Tran Quang Khai",
            "value": "21.0 km/h (free flow 38.0 km/h)",
            "source": "TomTom Traffic Flow",
        },
        {
            "label": "Hanoi city-wide US AQI",
            "value": "97",
            "source": "IQAir city-wide feed",
        },
        {
            "label": "Wind in Hoan Kiem",
            "value": "1.6 km/h",
            "source": "Open-Meteo weather model",
        },
    ]
    assert "not ground-sensor readings" in report["data_quality"]
