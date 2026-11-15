import pytest

from backend.recommendation import build_rotation_pairs, build_rotation_path


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
        ValueError,
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
