import httpx
import pytest
from fastapi import FastAPI
from pydantic import ValidationError

from backend.climate_analysis import (
    ClimateAnalysisError,
    InsufficientClimateDataError,
)
from backend.climate_pipeline import ClimatePipelineResult
from backend.main import (
    app,
    handle_climate_analysis_error,
    handle_insufficient_climate_data,
)
from backend.models import (
    AnalyzeRequest,
    ClimateAnalysisResult,
    DailyClimateRecord,
    MonthlyClimate,
    PlannedRotationAssessment,
    RecommendationScores,
)
from backend.nasa_service import ClimateDataResult, NasaServiceError


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


def test_analyze_request_rejects_more_than_five_years() -> None:
    with pytest.raises(ValidationError, match="en fazla 5 yıl"):
        AnalyzeRequest(
            latitude=40.195,
            longitude=29.06,
            start_date="2020-01-01",
            end_date="2025-12-31",
            previous_crop=None,
            current_crop="wheat",
            next_crop=None,
            soil_type="loamy",
            priority="balanced",
        )


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


@pytest.mark.asyncio
async def test_insufficient_climate_data_error_response() -> None:
    test_app = FastAPI()
    test_app.add_exception_handler(
        InsufficientClimateDataError,
        handle_insufficient_climate_data,
    )
    test_app.add_exception_handler(
        ClimateAnalysisError,
        handle_climate_analysis_error,
    )

    @test_app.get("/raise-error")
    async def raise_error() -> None:
        raise InsufficientClimateDataError("çekirdek veri yetersiz")

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/raise-error")

    assert response.status_code == 422
    assert response.json() == {
        "detail": {
            "code": "INSUFFICIENT_CLIMATE_DATA",
            "message": "çekirdek veri yetersiz",
        }
    }


@pytest.mark.asyncio
async def test_climate_analysis_error_response() -> None:
    test_app = FastAPI()
    test_app.add_exception_handler(
        ClimateAnalysisError,
        handle_climate_analysis_error,
    )

    @test_app.get("/raise-error")
    async def raise_error() -> None:
        raise ClimateAnalysisError("iklim kaydı geçersiz")

    transport = httpx.ASGITransport(app=test_app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/raise-error")

    assert response.status_code == 500
    assert response.json() == {
        "detail": {
            "code": "CLIMATE_ANALYSIS_ERROR",
            "message": "iklim kaydı geçersiz",
        }
    }


def _analysis_request_body(**overrides) -> dict:
    body = {
        "latitude": 40.195,
        "longitude": 29.06,
        "start_date": "2021-01-01",
        "end_date": "2025-12-31",
        "previous_crop": "wheat",
        "current_crop": "chickpea",
        "next_crop": "sunflower",
        "soil_type": "loamy",
        "priority": "water_saving",
    }
    body.update(overrides)
    return body


def _successful_pipeline_result() -> ClimatePipelineResult:
    analysis = ClimateAnalysisResult.model_validate(
        {
            "summary": {
                "average_temperature_c": 14.1,
                "minimum_temperature_c": -16.2,
                "maximum_temperature_c": 41.1,
                "total_precipitation_mm": 3099.6,
                "dry_days": 1347,
                "longest_dry_spell_days": 69,
                "hot_days": 71,
                "data_completeness_percent": 100.0,
            },
            "risk": {
                "level": "high",
                "score": 75,
                "reasons": ["Uzun kuru dönem tespit edildi."],
            },
            "monthly_climate": [
                {
                    "month": "2021-01",
                    "average_temperature_c": 4.3,
                    "precipitation_mm": 205.8,
                }
            ],
        }
    )
    return ClimatePipelineResult(
        source=ClimateDataResult(daily_records=[], mode="cache"),
        analysis=analysis,
    )


@pytest.mark.asyncio
async def test_crops_endpoint_returns_validated_crop_list() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/api/crops")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload["crops"]) == 9
    assert {crop["id"] for crop in payload["crops"]} == {
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


@pytest.mark.asyncio
async def test_analyze_endpoint_combines_climate_and_rotation(
    monkeypatch,
) -> None:
    async def fake_pipeline(**kwargs) -> ClimatePipelineResult:
        return _successful_pipeline_result()

    monkeypatch.setattr("backend.main.run_climate_pipeline", fake_pipeline)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/analyze",
            json=_analysis_request_body(),
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["location"]["label"] == "Bursa, Türkiye"
    assert payload["source"]["mode"] == "cache"
    assert payload["source"]["start_date"] == "2021-01-01"
    assert payload["source"]["end_date"] == "2025-12-31"
    assert payload["summary"]["total_precipitation_mm"] == 3099.6
    assert payload["planned_rotation_assessment"]["crop_id"] == "chickpea"
    assert len(payload["recommendations"]) <= 3
    assert all(
        item["crop_id"] != "chickpea"
        for item in payload["recommendations"]
    )


@pytest.mark.asyncio
async def test_analyze_endpoint_maps_invalid_crop_to_422(monkeypatch) -> None:
    async def fake_pipeline(**kwargs) -> ClimatePipelineResult:
        return _successful_pipeline_result()

    monkeypatch.setattr("backend.main.run_climate_pipeline", fake_pipeline)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/analyze",
            json=_analysis_request_body(current_crop="unknown"),
        )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INVALID_CROP_SELECTION"


@pytest.mark.asyncio
async def test_analyze_endpoint_maps_nasa_failure_to_502(monkeypatch) -> None:
    async def failing_pipeline(**kwargs) -> ClimatePipelineResult:
        raise NasaServiceError(
            "NASA_API_UNAVAILABLE",
            "NASA POWER verisine ulaşılamıyor.",
            status_code=503,
        )

    monkeypatch.setattr("backend.main.run_climate_pipeline", failing_pipeline)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/analyze",
            json=_analysis_request_body(),
        )

    assert response.status_code == 502
    assert response.json() == {
        "detail": {
            "code": "NASA_API_UNAVAILABLE",
            "message": "NASA POWER verisine ulaşılamıyor.",
        }
    }
