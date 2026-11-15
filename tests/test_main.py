import httpx
import pytest
from pydantic import ValidationError

from backend.main import app
from backend.models import (
    AnalyzeRequest,
    DailyClimateRecord,
    MonthlyClimate,
    PlannedRotationAssessment,
    RecommendationScores,
)


@pytest.mark.asyncio
async def test_health_endpoint() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "field-shift-api",
    }


def test_analyze_request_rejects_reverse_date_range() -> None:
    try:
        AnalyzeRequest(
            latitude=40.195,
            longitude=29.06,
            start_date="2025-01-02",
            end_date="2025-01-01",
            previous_crop=None,
            current_crop="wheat",
            next_crop=None,
            soil_type="loamy",
            priority="water_saving",
        )
    except ValidationError:
        return

    raise AssertionError("Ters tarih aralığı kabul edilmemeliydi.")


def test_daily_record_preserves_zero_and_accepts_optional_nulls() -> None:
    record = DailyClimateRecord(
        date="2021-01-01",
        temperature_c=5.4,
        temperature_min_c=1.8,
        temperature_max_c=9.1,
        precipitation_mm=0,
        relative_humidity_percent=None,
        root_zone_wetness=None,
    )

    assert record.precipitation_mm == 0
    assert record.relative_humidity_percent is None
    assert record.root_zone_wetness is None


def test_analyze_request_accepts_nullable_rotation_context() -> None:
    request = AnalyzeRequest(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2025-12-31",
        previous_crop=None,
        current_crop="chickpea",
        next_crop=None,
        soil_type="loamy",
        priority="water_saving",
    )

    assert request.previous_crop is None
    assert request.current_crop == "chickpea"
    assert request.next_crop is None


def test_analyze_request_accepts_fallow_as_previous_crop() -> None:
    request = AnalyzeRequest(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2025-12-31",
        previous_crop="fallow",
        current_crop="chickpea",
        next_crop="sunflower",
        soil_type="loamy",
        priority="balanced",
    )

    assert request.previous_crop == "fallow"


@pytest.mark.parametrize("field_name", ["current_crop", "next_crop"])
def test_fallow_is_allowed_only_for_previous_crop(field_name: str) -> None:
    values = {
        "latitude": 40.195,
        "longitude": 29.06,
        "start_date": "2021-01-01",
        "end_date": "2025-12-31",
        "previous_crop": "fallow",
        "current_crop": "chickpea",
        "next_crop": None,
        "soil_type": "loamy",
        "priority": "balanced",
    }
    values[field_name] = "fallow"

    with pytest.raises(ValidationError, match="yalnızca previous_crop"):
        AnalyzeRequest.model_validate(values)


def test_monthly_climate_preserves_zero_and_accepts_nulls() -> None:
    missing_temperature = MonthlyClimate(
        month="2021-01",
        average_temperature_c=None,
        precipitation_mm=0.0,
    )
    missing_precipitation = MonthlyClimate(
        month="2021-02",
        average_temperature_c=0.0,
        precipitation_mm=None,
    )

    assert missing_temperature.average_temperature_c is None
    assert missing_temperature.precipitation_mm == 0.0
    assert missing_precipitation.average_temperature_c == 0.0
    assert missing_precipitation.precipitation_mm is None


def test_planned_rotation_assessment_accepts_limitations() -> None:
    assessment = PlannedRotationAssessment(
        crop_id="chickpea",
        crop_name="Nohut",
        rotation=["fallow", "chickpea"],
        scores=RecommendationScores(
            total=80,
            climate=82,
            water=90,
            soil=78,
            rotation=70,
        ),
        advantages=["Su ihtiyacı düşüktür."],
        risks=[],
        limitations=["Önceki yıllara ait ayrıntılı geçmiş bulunmuyor."],
    )

    assert assessment.rotation == ["fallow", "chickpea"]
    assert assessment.limitations
