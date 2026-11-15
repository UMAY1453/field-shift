import httpx
import pytest
from pydantic import ValidationError

from backend.main import app
from backend.models import AnalyzeRequest, DailyClimateRecord


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
            current_crop="wheat",
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
