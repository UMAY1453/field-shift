"""NASA günlük verisi ile iklim analizi arasındaki entegrasyon katmanı."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from datetime import date
from typing import Any

from pydantic import ValidationError

from backend.climate_analysis import ClimateAnalysisError, analyze_climate
from backend.models import ClimateAnalysisResult
from backend.nasa_service import ClimateDataResult, get_climate_data


ClimateLoader = Callable[..., Awaitable[ClimateDataResult]]
ClimateAnalyzer = Callable[
    [list[dict[str, Any]]],
    dict[str, Any],
]


@dataclass(frozen=True, slots=True)
class ClimatePipelineResult:
    """Veri kaynağı bilgisi ile doğrulanmış analiz sonucunu birlikte taşır."""

    source: ClimateDataResult
    analysis: ClimateAnalysisResult


async def run_climate_pipeline(
    *,
    latitude: float,
    longitude: float,
    start_date: date | str,
    end_date: date | str,
    allow_verified_bursa_fallback: bool = False,
    climate_loader: ClimateLoader = get_climate_data,
    climate_analyzer: ClimateAnalyzer = analyze_climate,
) -> ClimatePipelineResult:
    """NASA kayıtlarını alır, analiz eder ve çıktı sözleşmesini doğrular."""

    source = await climate_loader(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
        allow_verified_bursa_fallback=allow_verified_bursa_fallback,
    )

    raw_analysis = await asyncio.to_thread(
        climate_analyzer,
        source.daily_records,
    )
    try:
        analysis = ClimateAnalysisResult.model_validate(raw_analysis)
    except ValidationError as exc:
        raise ClimateAnalysisError(
            "İklim analizi beklenen çıktı sözleşmesine uymuyor."
        ) from exc

    return ClimatePipelineResult(
        source=source,
        analysis=analysis,
    )
