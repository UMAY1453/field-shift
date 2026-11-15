from copy import deepcopy
from datetime import date, timedelta

import pytest

from backend.climate_analysis import analyze_climate
from backend.recommendation import (
    InvalidClimateResultError,
    InvalidCropSelectionError,
    InvalidRecommendationInputError,
    build_climate_limitations,
    build_minimum_return_limitations,
    build_rotation_pairs,
    build_rotation_path,
    calculate_annual_precipitation_mm,
    load_crops,
    recommend_rotations,
    validate_crop_selections,
    validate_recommendation_inputs,
)


def test_build_rotation_path_with_three_known_crops():
    assert build_rotation_path("wheat", "chickpea", "sunflower") == [
        "wheat",
        "chickpea",
        "sunflower",
    ]


def test_build_rotation_path_omits_unknown_previous_crop():
    assert build_rotation_path(None, "chickpea", "sunflower") == [
        "chickpea",
        "sunflower",
    ]


def test_build_rotation_path_preserves_fallow():
    assert build_rotation_path("fallow", "chickpea", "sunflower") == [
        "fallow",
        "chickpea",
        "sunflower",
    ]


def test_build_rotation_path_omits_unplanned_next_crop():
    assert build_rotation_path("wheat", "chickpea", None) == [
        "wheat",
        "chickpea",
    ]


def test_build_rotation_path_rejects_empty_candidate_crop():
    with pytest.raises(
        InvalidCropSelectionError,
        match="Değerlendirilecek ürün kimliği boş olamaz.",
    ):
        build_rotation_path("wheat", "", "sunflower")


def test_build_rotation_pairs_with_three_crops():
    assert build_rotation_pairs(["wheat", "chickpea", "sunflower"]) == [
        ("wheat", "chickpea"),
        ("chickpea", "sunflower"),
    ]


def test_build_rotation_pairs_with_single_crop():
    assert build_rotation_pairs(["chickpea"]) == []


def test_build_rotation_pairs_preserves_fallow_transition():
    assert build_rotation_pairs(["fallow", "chickpea"]) == [
        ("fallow", "chickpea"),
    ]


def test_validate_crop_selections_accepts_contract_values():
    crop_ids = {"wheat", "chickpea", "sunflower"}

    validate_crop_selections("fallow", "chickpea", None, crop_ids)
    validate_crop_selections(None, "chickpea", "sunflower", crop_ids)


@pytest.mark.parametrize(
    ("previous_crop", "current_crop", "next_crop"),
    [
        (None, "unknown", None),
        ("unknown", "wheat", None),
        (None, "wheat", "unknown"),
        (None, "fallow", None),
        (None, "wheat", "fallow"),
    ],
)
def test_validate_crop_selections_rejects_invalid_values(
    previous_crop,
    current_crop,
    next_crop,
):
    with pytest.raises(InvalidCropSelectionError):
        validate_crop_selections(
            previous_crop,
            current_crop,
            next_crop,
            {"wheat"},
        )


def test_validate_recommendation_inputs_accepts_contract_values():
    validate_recommendation_inputs(
        previous_crop="fallow",
        current_crop="wheat",
        next_crop="chickpea",
        soil_type="loamy",
        priority="water_saving",
        crop_ids={"wheat", "chickpea"},
    )


@pytest.mark.parametrize(
    ("soil_type", "priority", "message"),
    [
        ("peat", "balanced", "soil_type"),
        ("loamy", "profit", "priority"),
    ],
)
def test_validate_recommendation_inputs_rejects_invalid_contract_values(
    soil_type,
    priority,
    message,
):
    with pytest.raises(InvalidRecommendationInputError, match=message):
        validate_recommendation_inputs(
            previous_crop=None,
            current_crop="wheat",
            next_crop=None,
            soil_type=soil_type,
            priority=priority,
            crop_ids={"wheat"},
        )


def test_invalid_crop_error_is_an_input_error():
    assert issubclass(InvalidCropSelectionError, InvalidRecommendationInputError)


def test_calculate_annual_precipitation_for_five_year_period():
    climate_result = {
        "metadata": {
            "start_date": "2021-01-01",
            "end_date": "2025-12-31",
            "period_days": 1826,
        },
        "summary": {
            "total_precipitation_mm": 2500.0,
            "data_completeness_percent": 100.0,
        },
    }

    assert calculate_annual_precipitation_mm(climate_result) == pytest.approx(
        500.0,
        rel=0.001,
    )


@pytest.mark.parametrize(
    "climate_result",
    [
        {},
        {
            "metadata": {
                "start_date": "2025-01-02",
                "end_date": "2025-01-01",
                "period_days": 1,
            },
            "summary": {
                "total_precipitation_mm": 100.0,
                "data_completeness_percent": 100.0,
            },
        },
        {
            "metadata": {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "period_days": 365,
            },
            "summary": {
                "total_precipitation_mm": -1.0,
                "data_completeness_percent": 100.0,
            },
        },
        {
            "metadata": {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "period_days": 364,
            },
            "summary": {
                "total_precipitation_mm": 500.0,
                "data_completeness_percent": 100.0,
            },
        },
        {
            "metadata": {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
                "period_days": True,
            },
            "summary": {
                "total_precipitation_mm": 500.0,
                "data_completeness_percent": 100.0,
            },
        },
    ],
)
def test_calculate_annual_precipitation_rejects_invalid_climate_result(
    climate_result,
):
    with pytest.raises(InvalidClimateResultError):
        calculate_annual_precipitation_mm(climate_result)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("total_precipitation_mm", True),
        ("total_precipitation_mm", float("nan")),
        ("total_precipitation_mm", float("inf")),
        ("total_precipitation_mm", float("-inf")),
        ("data_completeness_percent", True),
        ("data_completeness_percent", float("nan")),
        ("data_completeness_percent", float("inf")),
        ("data_completeness_percent", -0.1),
        ("data_completeness_percent", 100.1),
    ],
)
def test_climate_numeric_fields_reject_invalid_values(field, invalid_value):
    climate_result = {
        "metadata": {
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "period_days": 365,
        },
        "summary": {
            "total_precipitation_mm": 500.0,
            "data_completeness_percent": 100.0,
        },
    }
    climate_result["summary"][field] = invalid_value

    with pytest.raises(InvalidClimateResultError):
        calculate_annual_precipitation_mm(climate_result)


def test_incomplete_climate_data_adds_a_limitation():
    climate_result = {
        "metadata": {
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "period_days": 365,
        },
        "summary": {
            "total_precipitation_mm": 500.0,
            "data_completeness_percent": 98.9,
        },
    }

    limitations = build_climate_limitations(climate_result)

    assert len(limitations) == 1
    assert "%98.9" in limitations[0]
    assert "yıllık yağış" in limitations[0]


def test_complete_climate_data_adds_no_limitation():
    climate_result = {
        "metadata": {
            "start_date": "2025-01-01",
            "end_date": "2025-12-31",
            "period_days": 365,
        },
        "summary": {
            "total_precipitation_mm": 500.0,
            "data_completeness_percent": 100.0,
        },
    }

    assert build_climate_limitations(climate_result) == []


def test_minimum_return_years_are_reported_as_a_limitation():
    crops_by_id = load_crops()

    limitations = build_minimum_return_limitations(
        ["wheat", "processing_tomato", "lentil"],
        crops_by_id,
    )

    assert len(limitations) == 2
    assert "3 yıldır" in limitations[0]
    assert "2 yıldır" in limitations[1]


@pytest.fixture
def complete_climate_result():
    return {
        "summary": {
            "average_temperature_c": 18.0,
            "minimum_temperature_c": 6.0,
            "maximum_temperature_c": 34.0,
            "total_precipitation_mm": 3000.0,
            "dry_days": 600,
            "longest_dry_spell_days": 22,
            "hot_days": 12,
            "data_completeness_percent": 98.9,
        },
        "risk": {
            "level": "medium",
            "score": 58,
            "reasons": ["Uzun kurak dönem tespit edildi."],
        },
        "monthly_climate": [],
        "metadata": {
            "start_date": "2021-01-01",
            "end_date": "2025-12-31",
            "period_days": 1826,
        },
    }


def test_recommend_rotations_matches_contract_shape(complete_climate_result):
    result = recommend_rotations(
        previous_crop="wheat",
        current_crop="chickpea",
        next_crop="sunflower",
        soil_type="loamy",
        priority="balanced",
        climate_result=complete_climate_result,
    )

    assert set(result) == {"planned_rotation_assessment", "recommendations"}

    planned = result["planned_rotation_assessment"]
    assert set(planned) == {
        "crop_id",
        "crop_name",
        "rotation",
        "scores",
        "advantages",
        "risks",
        "limitations",
    }
    assert set(planned["scores"]) == {
        "total",
        "climate",
        "water",
        "soil",
        "rotation",
    }
    assert planned["crop_id"] == "chickpea"
    assert planned["rotation"] == ["wheat", "chickpea", "sunflower"]

    assert len(result["recommendations"]) <= 3
    for recommendation in result["recommendations"]:
        assert set(recommendation) == {
            "rank",
            "crop_id",
            "crop_name",
            "rotation",
            "scores",
            "advantages",
            "risks",
        }


def test_recommendations_exclude_current_crop_and_have_sequential_ranks(
    complete_climate_result,
):
    result = recommend_rotations(
        previous_crop="wheat",
        current_crop="chickpea",
        next_crop=None,
        soil_type="loamy",
        priority="water_saving",
        climate_result=complete_climate_result,
    )

    recommendations = result["recommendations"]
    assert all(item["crop_id"] != "chickpea" for item in recommendations)
    assert [item["rank"] for item in recommendations] == list(
        range(1, len(recommendations) + 1)
    )


def test_recommendations_are_deterministic(complete_climate_result):
    arguments = {
        "previous_crop": "fallow",
        "current_crop": "wheat",
        "next_crop": None,
        "soil_type": "loamy",
        "priority": "balanced",
        "climate_result": complete_climate_result,
    }

    first_result = recommend_rotations(**arguments)
    second_result = recommend_rotations(**arguments)

    assert first_result == second_result


def test_recommend_rotations_does_not_mutate_climate_result(
    complete_climate_result,
):
    original = deepcopy(complete_climate_result)

    recommend_rotations(
        previous_crop=None,
        current_crop="wheat",
        next_crop=None,
        soil_type="loamy",
        priority="yield",
        climate_result=complete_climate_result,
    )

    assert complete_climate_result == original


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [
        ("average_temperature_c", True),
        ("average_temperature_c", float("nan")),
        ("minimum_temperature_c", float("inf")),
        ("maximum_temperature_c", float("-inf")),
    ],
)
def test_recommend_rotations_rejects_invalid_temperature_values(
    complete_climate_result,
    field,
    invalid_value,
):
    complete_climate_result["summary"][field] = invalid_value

    with pytest.raises(InvalidClimateResultError):
        recommend_rotations(
            previous_crop=None,
            current_crop="wheat",
            next_crop=None,
            soil_type="loamy",
            priority="balanced",
            climate_result=complete_climate_result,
        )


def test_planned_assessment_includes_climate_data_limitation(
    complete_climate_result,
):
    result = recommend_rotations(
        previous_crop=None,
        current_crop="processing_tomato",
        next_crop=None,
        soil_type="loamy",
        priority="balanced",
        climate_result=complete_climate_result,
    )

    limitations = result["planned_rotation_assessment"]["limitations"]
    assert any("%98.9" in limitation for limitation in limitations)
    assert any("3 yıldır" in limitation for limitation in limitations)
    assert any("Önceki ürün bilinmediği" in limitation for limitation in limitations)
    assert any("Sonraki ürün planlanmadığı" in limitation for limitation in limitations)


def test_climate_analysis_output_integrates_with_recommendation_engine():
    start_date = date(2025, 1, 1)
    daily_records = []

    for day_offset in range(10):
        record_date = start_date + timedelta(days=day_offset)
        daily_records.append(
            {
                "date": record_date.isoformat(),
                "temperature_c": 18.0 + day_offset * 0.1,
                "temperature_min_c": 8.0,
                "temperature_max_c": 29.0,
                "precipitation_mm": 2.0,
                "relative_humidity_percent": 65.0,
                "root_zone_wetness": 0.55,
            }
        )

    climate_result = analyze_climate(daily_records)
    original_climate_result = deepcopy(climate_result)
    enriched_climate_result = {
        **climate_result,
        "metadata": {
            "start_date": daily_records[0]["date"],
            "end_date": daily_records[-1]["date"],
            "period_days": len(daily_records),
        },
    }

    result = recommend_rotations(
        previous_crop="wheat",
        current_crop="chickpea",
        next_crop="sunflower",
        soil_type="loamy",
        priority="balanced",
        climate_result=enriched_climate_result,
    )

    assert climate_result == original_climate_result
    assert "metadata" not in climate_result
    assert result["planned_rotation_assessment"]["crop_id"] == "chickpea"
    assert len(result["recommendations"]) <= 3
    assert [item["rank"] for item in result["recommendations"]] == list(
        range(1, len(result["recommendations"]) + 1)
    )
