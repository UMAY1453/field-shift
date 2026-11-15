import json
from pathlib import Path

import pytest


CROPS_PATH = Path(__file__).parents[1] / "backend" / "data" / "crops.json"

EXPECTED_CROP_IDS = {
    "wheat",
    "barley",
    "corn",
    "chickpea",
    "sunflower",
    "canola",
    "potato",
    "processing_tomato",
    "lentil",
}

REQUIRED_FIELDS = {
    "id",
    "name",
    "family",
    "is_legume",
    "growing_season",
    "water_need",
    "suitable_soils",
    "soil_notes",
    "temperature_range_c",
    "absolute_temperature_range_c",
    "temperature_notes",
    "annual_precipitation_range_mm",
    "rotation",
    "sources",
}

ALLOWED_SEASONS = {"spring", "summer", "autumn", "winter"}
ALLOWED_WATER_NEEDS = {"low", "medium", "high"}
ALLOWED_SOILS = {"sandy", "loamy", "clay", "silty"}


@pytest.fixture(scope="module")
def crops():
    return json.loads(CROPS_PATH.read_text(encoding="utf-8"))


def test_crops_json_root_is_a_list(crops):
    assert isinstance(crops, list)


def test_expected_crop_ids_are_present_and_unique(crops):
    crop_ids = [crop["id"] for crop in crops]

    assert set(crop_ids) == EXPECTED_CROP_IDS
    assert len(crop_ids) == len(set(crop_ids))


@pytest.mark.parametrize("range_field", [
    "temperature_range_c",
    "absolute_temperature_range_c",
    "annual_precipitation_range_mm",
])
def test_numeric_ranges_have_ordered_minimum_and_maximum(crops, range_field):
    for crop in crops:
        value_range = crop[range_field]

        assert set(value_range) == {"min", "max"}, crop["id"]
        assert isinstance(value_range["min"], (int, float)), crop["id"]
        assert isinstance(value_range["max"], (int, float)), crop["id"]
        assert value_range["min"] < value_range["max"], crop["id"]


def test_crop_fields_use_contract_values(crops):
    for crop in crops:
        assert REQUIRED_FIELDS <= set(crop), crop["id"]
        assert isinstance(crop["name"], str) and crop["name"].strip()
        assert isinstance(crop["family"], str) and crop["family"].strip()
        assert isinstance(crop["is_legume"], bool)
        assert crop["growing_season"], crop["id"]
        assert set(crop["growing_season"]) <= ALLOWED_SEASONS, crop["id"]
        assert crop["water_need"] in ALLOWED_WATER_NEEDS, crop["id"]
        assert crop["suitable_soils"], crop["id"]
        assert set(crop["suitable_soils"]) <= ALLOWED_SOILS, crop["id"]
        assert isinstance(crop["soil_notes"], list), crop["id"]
        assert isinstance(crop["temperature_notes"], list), crop["id"]


def test_optimal_temperature_is_inside_absolute_limits(crops):
    for crop in crops:
        optimal = crop["temperature_range_c"]
        absolute = crop["absolute_temperature_range_c"]

        assert absolute["min"] <= optimal["min"], crop["id"]
        assert optimal["max"] <= absolute["max"], crop["id"]


def test_rotation_fields_and_references_are_valid(crops):
    allowed_rotation_ids = EXPECTED_CROP_IDS | {"fallow"}

    for crop in crops:
        rotation = crop["rotation"]
        return_years = rotation["minimum_return_years"]

        assert return_years is None or (
            isinstance(return_years, int) and return_years > 0
        ), crop["id"]
        assert isinstance(rotation["avoid_continuous_cropping"], bool)
        assert isinstance(rotation["example_rotations"], list)
        assert isinstance(rotation["disease_groups"], list)
        assert isinstance(rotation["notes"], list)

        for path in rotation["example_rotations"]:
            assert isinstance(path, list) and len(path) >= 2, crop["id"]
            assert set(path) <= allowed_rotation_ids, crop["id"]


def test_sources_are_present_and_structured(crops):
    for crop in crops:
        assert crop["sources"], crop["id"]

        for source in crop["sources"]:
            assert set(source) == {"title", "url", "supports"}, crop["id"]
            assert isinstance(source["title"], str) and source["title"].strip()
            assert source["url"].startswith("https://"), crop["id"]
            assert isinstance(source["supports"], list) and source["supports"]
