import agent
import investigation


def test_comparisons_do_not_offer_the_single_district_history_tool():
    normal_tools = {tool["name"] for tool in agent._tools_for_request(None)}
    comparison_tools = {tool["name"] for tool in agent._tools_for_request("Tay Ho")}

    assert "get_district_history" in normal_tools
    assert "get_district_history" not in comparison_tools
    assert "compare_district_evidence" in comparison_tools


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


def test_inspection_summary_starts_with_verified_aqi_history_and_aqi_meaning():
    report = {"summary": "Low wind may limit dispersion."}

    agent._prepend_inspection_evidence_lead(
        report,
        {
            "district_name": "Hoan Kiem",
            "district_us_aqi": 159,
            "district_pm2_5_ug_m3": 156.5,
        },
        [
            {"us_aqi": 100.0, "pm2_5_ug_m3": 100.0},
            {"us_aqi": 110.0, "pm2_5_ug_m3": 110.0},
        ],
    )

    assert report["summary"].startswith(
        "The current CAMS-modelled US AQI is elevated at 159, 51% above the recent district median of 105; "
        "higher AQI values indicate worse modelled air quality."
    )
    assert "Modelled PM2.5 is elevated at 156.5 µg/m³, 49% above the recent district median of 105.0 µg/m³." in report["summary"]


def test_comparison_keeps_both_districts_source_controlled():
    report = {
        "title": "Inspection",
        "summary": "A cautious summary.",
        "numeric_summary": [],
    }
    agent._apply_comparison(
        report,
        {
            "district_name": "Dong Da",
            "district_us_aqi": 159,
            "district_pm2_5_ug_m3": 156.5,
            "wind_speed_kmh": 1.3,
            "traffic_road_name": "Tay Son",
            "traffic_current_speed_kmh": 20.0,
            "traffic_free_flow_speed_kmh": 38.0,
        },
        {
            "district_name": "Ba Dinh",
            "district_us_aqi": 147,
            "district_pm2_5_ug_m3": 123.4,
            "wind_speed_kmh": 1.5,
            "traffic_road_name": "Kim Ma",
            "traffic_current_speed_kmh": 18.0,
            "traffic_free_flow_speed_kmh": 39.0,
        },
    )

    assert report["title"] == "Air-quality comparison — Dong Da vs Ba Dinh"
    assert "Dong Da has the higher" in report["summary"]
    assert len(report["numeric_summary"]) == 8
    assert report["numeric_summary"][-1]["source"] == "TomTom Traffic Flow"
    assert [item["label"] for item in report["numeric_summary"]] == [
        "Dong Da modelled US AQI",
        "Ba Dinh modelled US AQI",
        "Dong Da modelled PM2.5",
        "Ba Dinh modelled PM2.5",
        "Wind in Dong Da",
        "Wind in Ba Dinh",
        "Traffic on Tay Son",
        "Traffic on Kim Ma",
    ]
    assert "CAMS model estimates" in report["comparison_note"]


def test_comparison_describes_equal_aqi_without_picking_a_higher_district():
    report = {"title": "Inspection", "summary": "A cautious summary.", "numeric_summary": []}
    agent._apply_comparison(
        report,
        {"district_name": "Long Bien", "district_us_aqi": 138},
        {"district_name": "Ba Dinh", "district_us_aqi": 138},
    )

    assert "Long Bien and Ba Dinh have the same current CAMS-modelled AQI of 138." in report["summary"]
    assert "higher current CAMS-modelled AQI" not in report["summary"]
