from datetime import date, timedelta

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
    DEFAULT_REFERENCE_END_DATE,
    DEFAULT_REFERENCE_START_DATE,
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


@pytest.mark.asyncio
async def test_root_serves_frontend() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Field Shift" in response.text


def test_analyze_request_rejects_reverse_date_range() -> None:
    try:
        AnalyzeRequest(
            latitude=40.195,
            longitude=29.06,
            start_date="2025-01-02",
            end_date="2025-01-01",
            previous_crop="wheat",
            current_crop="wheat",
            next_crop="sunflower",
            soil_type="loamy",
            priority="water_saving",
            harvest_start_date="2027-08-15",
            harvest_end_date="2027-09-15",
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
            previous_crop="wheat",
            current_crop="wheat",
            next_crop="sunflower",
            soil_type="loamy",
            priority="balanced",
            harvest_start_date="2027-08-15",
            harvest_end_date="2027-09-15",
        )


def test_analyze_request_accepts_1827_day_five_year_period() -> None:
    request = AnalyzeRequest(
        latitude=40.195,
        longitude=29.06,
        start_date="2024-01-01",
        end_date="2028-12-31",
        previous_crop="wheat",
        current_crop="corn",
        next_crop="sunflower",
        soil_type="loamy",
        priority="balanced",
        harvest_start_date="2029-08-15",
        harvest_end_date="2029-09-15",
    )

    assert (request.end_date - request.start_date).days + 1 == 1827


def test_analyze_request_requires_both_reference_dates() -> None:
    with pytest.raises(ValidationError, match="birlikte gönderilmelidir"):
        AnalyzeRequest(
            latitude=40.195,
            longitude=29.06,
            start_date="2024-01-01",
            previous_crop="wheat",
            current_crop="corn",
            next_crop="sunflower",
            soil_type="loamy",
            priority="balanced",
            harvest_start_date="2029-08-15",
            harvest_end_date="2029-09-15",
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


@pytest.mark.parametrize("missing_field", ["previous_crop", "next_crop"])
def test_analyze_request_requires_complete_rotation_plan(
    missing_field: str,
) -> None:
    values = {
        "latitude": 40.195,
        "longitude": 29.06,
        "previous_crop": "wheat",
        "current_crop": "chickpea",
        "next_crop": "sunflower",
        "soil_type": "loamy",
        "priority": "water_saving",
        "harvest_start_date": "2027-08-15",
        "harvest_end_date": "2027-09-15",
    }
    values.pop(missing_field)

    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(values)


def test_analyze_request_uses_default_reference_period() -> None:
    request = AnalyzeRequest(
        latitude=40.195,
        longitude=29.06,
        previous_crop="wheat",
        current_crop="corn",
        next_crop="sunflower",
        soil_type="loamy",
        priority="water_saving",
        harvest_start_date="2027-08-15",
        harvest_end_date="2027-09-15",
    )

    assert request.start_date == DEFAULT_REFERENCE_START_DATE
    assert request.end_date == DEFAULT_REFERENCE_END_DATE
    assert request.uses_automatic_reference_period is True


def test_analyze_request_still_accepts_custom_reference_period() -> None:
    request = AnalyzeRequest(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2021-06-30",
        previous_crop="wheat",
        current_crop="corn",
        next_crop="sunflower",
        soil_type="loamy",
        priority="balanced",
        harvest_start_date="2027-08-15",
        harvest_end_date="2027-09-15",
    )

    assert request.start_date.isoformat() == "2021-01-01"
    assert request.end_date.isoformat() == "2021-06-30"
    assert request.uses_automatic_reference_period is False


def test_analyze_request_keeps_current_crop_required() -> None:
    with pytest.raises(ValidationError):
        AnalyzeRequest.model_validate(
            {
                "latitude": 40.195,
                "longitude": 29.06,
                "previous_crop": "wheat",
                "next_crop": "sunflower",
                "soil_type": "loamy",
                "priority": "balanced",
                "harvest_start_date": "2027-08-15",
                "harvest_end_date": "2027-09-15",
            }
        )


def test_analyze_request_requires_valid_harvest_period() -> None:
    with pytest.raises(ValidationError, match="Hasat başlangıç tarihi"):
        AnalyzeRequest(
            latitude=40.195,
            longitude=29.06,
            previous_crop="wheat",
            current_crop="corn",
            next_crop="sunflower",
            soil_type="loamy",
            priority="balanced",
            harvest_start_date="2027-09-15",
            harvest_end_date="2027-08-15",
        )


def test_analyze_request_rejects_harvest_period_over_120_days() -> None:
    with pytest.raises(ValidationError, match="en fazla 120 gün"):
        AnalyzeRequest(
            latitude=40.195,
            longitude=29.06,
            previous_crop="wheat",
            current_crop="corn",
            next_crop="sunflower",
            soil_type="loamy",
            priority="balanced",
            harvest_start_date="2027-01-01",
            harvest_end_date="2027-05-31",
        )


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
        harvest_start_date="2027-08-15",
        harvest_end_date="2027-09-15",
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
        "next_crop": "sunflower",
        "soil_type": "loamy",
        "priority": "balanced",
        "harvest_start_date": "2027-08-15",
        "harvest_end_date": "2027-09-15",
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
        "harvest_start_date": "2027-08-15",
        "harvest_end_date": "2027-08-17",
    }
    body.update(overrides)
    return body


def _successful_pipeline_result(
    *,
    source_start_date: date | None = None,
    source_end_date: date | None = None,
    fallback_used: bool = False,
    warnings: list[str] | None = None,
) -> ClimatePipelineResult:
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
    daily_records = []
    for year in range(2021, 2026):
        period_start = date(year, 8, 15)
        for offset in range(3):
            record_date = period_start + timedelta(days=offset)
            daily_records.append(
                {
                    "date": record_date.isoformat(),
                    "temperature_c": 24.0 + offset,
                    "temperature_min_c": 18.0 + offset,
                    "temperature_max_c": 32.0 + offset,
                    "precipitation_mm": float(offset),
                    "relative_humidity_percent": 60.0,
                    "root_zone_wetness": 0.5,
                }
            )
    return ClimatePipelineResult(
        source=ClimateDataResult(
            daily_records=daily_records,
            mode="cache",
            start_date=source_start_date,
            end_date=source_end_date,
            fallback_used=fallback_used,
            warnings=warnings or [],
        ),
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
    assert payload["source"]["requested_start_date"] == "2021-01-01"
    assert payload["source"]["requested_end_date"] == "2025-12-31"
    assert payload["source"]["start_date"] == "2021-01-01"
    assert payload["source"]["end_date"] == "2025-12-31"
    assert payload["source"]["last_complete_year"] == 2025
    assert payload["source"]["is_latest_complete_period"] is True
    assert payload["source"]["fallback_used"] is False
    assert payload["source"]["warnings"] == []
    assert payload["summary"]["total_precipitation_mm"] == 3099.6
    assert payload["harvest_period_climate"]["seasons_analyzed"] == 5
    assert payload["harvest_period_climate"]["period_days"] == 3
    assert payload["planned_rotation_assessment"]["crop_id"] == "chickpea"
    assert len(payload["recommendations"]) <= 3
    assert all(
        item["crop_id"] != "chickpea"
        for item in payload["recommendations"]
    )


@pytest.mark.asyncio
async def test_analyze_endpoint_uses_default_climate_reference_period(
    monkeypatch,
) -> None:
    received_pipeline_arguments = {}

    async def fake_pipeline(**kwargs) -> ClimatePipelineResult:
        received_pipeline_arguments.update(kwargs)
        return _successful_pipeline_result()

    monkeypatch.setattr("backend.main.run_climate_pipeline", fake_pipeline)

    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/api/analyze",
            json={
                "latitude": 40.195,
                "longitude": 29.06,
                "previous_crop": "wheat",
                "current_crop": "corn",
                "next_crop": "sunflower",
                "soil_type": "loamy",
                "priority": "water_saving",
                "harvest_start_date": "2027-08-15",
                "harvest_end_date": "2027-08-17",
            },
        )

    assert response.status_code == 200
    assert received_pipeline_arguments["start_date"] == DEFAULT_REFERENCE_START_DATE
    assert received_pipeline_arguments["end_date"] == DEFAULT_REFERENCE_END_DATE
    payload = response.json()
    assert payload["source"]["start_date"] == "2021-01-01"
    assert payload["source"]["end_date"] == "2025-12-31"
    assert payload["planned_rotation_assessment"]["crop_id"] == "corn"


@pytest.mark.asyncio
async def test_analyze_endpoint_uses_actual_fallback_dates_everywhere(
    monkeypatch,
) -> None:
    received_pipeline_arguments = {}
    captured_climate_result = {}

    async def fake_pipeline(**kwargs) -> ClimatePipelineResult:
        received_pipeline_arguments.update(kwargs)
        return _successful_pipeline_result(
            source_start_date=date(2020, 1, 1),
            source_end_date=date(2024, 12, 31),
            fallback_used=True,
            warnings=["Doğrulanmış yedek dönem kullanıldı."],
        )

    original_recommend = __import__(
        "backend.main", fromlist=["recommend_rotations"]
    ).recommend_rotations

    def capturing_recommend(**kwargs):
        captured_climate_result.update(kwargs["climate_result"])
        return original_recommend(**kwargs)

    monkeypatch.setattr("backend.main.run_climate_pipeline", fake_pipeline)
    monkeypatch.setattr("backend.main.recommend_rotations", capturing_recommend)

    body = _analysis_request_body()
    body.pop("start_date")
    body.pop("end_date")
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post("/api/analyze", json=body)

    assert response.status_code == 200
    assert received_pipeline_arguments["allow_verified_bursa_fallback"] is True
    assert captured_climate_result["metadata"] == {
        "start_date": "2020-01-01",
        "end_date": "2024-12-31",
        "period_days": 1827,
    }
    source = response.json()["source"]
    assert source["requested_start_date"] == "2021-01-01"
    assert source["requested_end_date"] == "2025-12-31"
    assert source["start_date"] == "2020-01-01"
    assert source["end_date"] == "2024-12-31"
    assert source["fallback_used"] is True
    assert source["is_latest_complete_period"] is False
    assert source["warnings"] == ["Doğrulanmış yedek dönem kullanıldı."]


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
