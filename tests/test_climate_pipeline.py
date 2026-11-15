import json
from pathlib import Path
from typing import Literal

import pytest

from backend.climate_analysis import (
    ClimateAnalysisError,
    InsufficientClimateDataError,
)
from backend.climate_pipeline import run_climate_pipeline
from backend.nasa_service import ClimateDataResult


DEMO_PATH = (
    Path(__file__).parents[1]
    / "backend"
    / "data"
    / "demo_climate.json"
)


def _one_day_records() -> list[dict]:
    return [
        {
            "date": "2021-01-01",
            "temperature_c": 7.42,
            "temperature_min_c": 5.31,
            "temperature_max_c": 10.64,
            "precipitation_mm": 0.0,
            "relative_humidity_percent": 92.9,
            "root_zone_wetness": 0.44,
        }
    ]


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["live", "cache", "demo"])
async def test_pipeline_analyzes_every_source_mode(
    mode: Literal["live", "cache", "demo"],
) -> None:
    async def climate_loader(**kwargs) -> ClimateDataResult:
        return ClimateDataResult(
            daily_records=_one_day_records(),
            mode=mode,
        )

    result = await run_climate_pipeline(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2021-01-01",
        climate_loader=climate_loader,
    )

    assert result.source.mode == mode
    assert result.analysis.summary.total_precipitation_mm == 0.0
    assert result.analysis.summary.data_completeness_percent == 100.0
    assert result.analysis.monthly_climate[0].month == "2021-01"


@pytest.mark.asyncio
async def test_pipeline_preserves_analysis_errors() -> None:
    async def climate_loader(**kwargs) -> ClimateDataResult:
        return ClimateDataResult(
            daily_records=_one_day_records(),
            mode="cache",
        )

    def failing_analyzer(daily_records: list[dict]) -> dict:
        raise InsufficientClimateDataError("çekirdek veri yetersiz")

    with pytest.raises(
        InsufficientClimateDataError,
        match="çekirdek veri yetersiz",
    ):
        await run_climate_pipeline(
            latitude=40.195,
            longitude=29.06,
            start_date="2021-01-01",
            end_date="2021-01-01",
            climate_loader=climate_loader,
            climate_analyzer=failing_analyzer,
        )


@pytest.mark.asyncio
async def test_pipeline_rejects_invalid_analysis_contract() -> None:
    async def climate_loader(**kwargs) -> ClimateDataResult:
        return ClimateDataResult(
            daily_records=_one_day_records(),
            mode="live",
        )

    def invalid_analyzer(daily_records: list[dict]) -> dict:
        return {"summary": {}}

    with pytest.raises(
        ClimateAnalysisError,
        match="çıktı sözleşmesine uymuyor",
    ):
        await run_climate_pipeline(
            latitude=40.195,
            longitude=29.06,
            start_date="2021-01-01",
            end_date="2021-01-01",
            climate_loader=climate_loader,
            climate_analyzer=invalid_analyzer,
        )


@pytest.mark.asyncio
async def test_pipeline_analyzes_committed_five_year_demo() -> None:
    records = json.loads(DEMO_PATH.read_text(encoding="utf-8"))

    async def climate_loader(**kwargs) -> ClimateDataResult:
        return ClimateDataResult(
            daily_records=records,
            mode="demo",
        )

    result = await run_climate_pipeline(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2025-12-31",
        climate_loader=climate_loader,
    )

    assert result.source.mode == "demo"
    assert result.analysis.summary.data_completeness_percent == 100.0
    assert len(result.analysis.monthly_climate) == 60
    assert result.analysis.monthly_climate[0].month == "2021-01"
    assert result.analysis.monthly_climate[-1].month == "2025-12"
