import pytest

from backend.recommendation import (
    InvalidClimateResultError,
    InvalidCropSelectionError,
    build_minimum_return_limitations,
    build_rotation_pairs,
    build_rotation_path,
    calculate_annual_precipitation_mm,
    load_crops,
    validate_crop_selections,
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


def test_calculate_annual_precipitation_for_five_year_period():
    climate_result = {
        "metadata": {
            "start_date": "2021-01-01",
            "end_date": "2025-12-31",
        },
        "summary": {"total_precipitation_mm": 2500.0},
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
            },
            "summary": {"total_precipitation_mm": 100.0},
        },
        {
            "metadata": {
                "start_date": "2025-01-01",
                "end_date": "2025-12-31",
            },
            "summary": {"total_precipitation_mm": -1.0},
        },
    ],
)
def test_calculate_annual_precipitation_rejects_invalid_climate_result(
    climate_result,
):
    with pytest.raises(InvalidClimateResultError):
        calculate_annual_precipitation_mm(climate_result)


def test_minimum_return_years_are_reported_as_a_limitation():
    crops_by_id = load_crops()

    limitations = build_minimum_return_limitations(
        ["wheat", "processing_tomato", "lentil"],
        crops_by_id,
    )

    assert len(limitations) == 2
    assert "3 yıldır" in limitations[0]
    assert "2 yıldır" in limitations[1]
