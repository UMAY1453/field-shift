"""Planlanan hasat aralığını tarihsel günlük iklim verisiyle karşılaştırır."""

from __future__ import annotations

from datetime import date, timedelta
import math
from statistics import fmean
from typing import Any


RAINY_DAY_THRESHOLD_MM = 1.0
HOT_DAY_THRESHOLD_C = 35.0


class HarvestAnalysisError(ValueError):
    """Hasat dönemi tarihsel veriden güvenilir biçimde üretilemediğinde oluşur."""


def _parse_record_date(value: object) -> date:
    if isinstance(value, date):
        return value
    if not isinstance(value, str):
        raise HarvestAnalysisError("Günlük iklim kaydının tarihi geçersiz.")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise HarvestAnalysisError(
            "Günlük iklim kaydının tarihi geçersiz."
        ) from exc


def _valid_number(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if math.isfinite(number) else None


def _average_or_none(values: list[float]) -> float | None:
    return round(fmean(values), 1) if values else None


def analyze_harvest_period(
    daily_records: list[dict[str, Any]],
    *,
    harvest_start_date: date,
    harvest_end_date: date,
) -> dict[str, Any]:
    """Aynı hasat aralığının tam tarihsel örneklerinden iklim özeti üretir."""

    if harvest_start_date > harvest_end_date:
        raise HarvestAnalysisError(
            "Hasat başlangıç tarihi, bitiş tarihinden sonra olamaz."
        )
    if not daily_records:
        raise HarvestAnalysisError(
            "Hasat dönemi için günlük iklim kaydı bulunamadı."
        )

    period_days = (harvest_end_date - harvest_start_date).days + 1
    records_by_date: dict[date, dict[str, Any]] = {}
    for record in daily_records:
        if not isinstance(record, dict):
            raise HarvestAnalysisError("Günlük iklim kaydı geçersiz.")
        record_date = _parse_record_date(record.get("date"))
        if record_date in records_by_date:
            raise HarvestAnalysisError(
                "Hasat analizinde tekrarlı günlük tarih bulundu."
            )
        records_by_date[record_date] = record

    first_available_date = min(records_by_date)
    last_available_date = max(records_by_date)
    windows: list[tuple[date, date, list[dict[str, Any] | None]]] = []

    for historical_year in range(
        first_available_date.year,
        last_available_date.year + 1,
    ):
        try:
            historical_start = harvest_start_date.replace(
                year=historical_year
            )
        except ValueError:
            # 29 Şubat yalnızca artık yıllarda karşılaştırılabilir.
            continue
        historical_end = historical_start + timedelta(days=period_days - 1)
        if (
            historical_start < first_available_date
            or historical_end > last_available_date
        ):
            continue

        window_records = [
            records_by_date.get(historical_start + timedelta(days=offset))
            for offset in range(period_days)
        ]
        windows.append((historical_start, historical_end, window_records))

    if not windows:
        raise HarvestAnalysisError(
            "Planlanan hasat aralığı için tam bir tarihsel dönem bulunamadı."
        )

    temperatures: list[float] = []
    maximum_temperatures: list[float] = []
    precipitation_per_period: list[float] = []
    rainy_days_per_period: list[float] = []
    hot_days_per_period: list[float] = []
    valid_measurements = 0
    expected_measurements = len(windows) * period_days * 3

    for _, _, records in windows:
        period_precipitation: list[float] = []
        rainy_days = 0
        hot_days = 0

        for record in records:
            if record is None:
                continue
            temperature = _valid_number(record.get("temperature_c"))
            maximum_temperature = _valid_number(
                record.get("temperature_max_c")
            )
            precipitation = _valid_number(record.get("precipitation_mm"))

            if temperature is not None:
                temperatures.append(temperature)
                valid_measurements += 1
            if maximum_temperature is not None:
                maximum_temperatures.append(maximum_temperature)
                valid_measurements += 1
                if maximum_temperature >= HOT_DAY_THRESHOLD_C:
                    hot_days += 1
            if precipitation is not None:
                period_precipitation.append(precipitation)
                valid_measurements += 1
                if precipitation >= RAINY_DAY_THRESHOLD_MM:
                    rainy_days += 1

        if period_precipitation:
            precipitation_per_period.append(sum(period_precipitation))
            rainy_days_per_period.append(float(rainy_days))
        if any(
            _valid_number(record.get("temperature_max_c")) is not None
            for record in records
            if record is not None
        ):
            hot_days_per_period.append(float(hot_days))

    completeness = (
        round(valid_measurements / expected_measurements * 100, 1)
        if expected_measurements
        else 0.0
    )

    return {
        "planned_start_date": harvest_start_date.isoformat(),
        "planned_end_date": harvest_end_date.isoformat(),
        "period_days": period_days,
        "seasons_analyzed": len(windows),
        "historical_windows": [
            {
                "start_date": start.isoformat(),
                "end_date": end.isoformat(),
            }
            for start, end, _ in windows
        ],
        "average_temperature_c": _average_or_none(temperatures),
        "average_maximum_temperature_c": _average_or_none(
            maximum_temperatures
        ),
        "average_precipitation_mm_per_period": _average_or_none(
            precipitation_per_period
        ),
        "average_rainy_days_per_period": _average_or_none(
            rainy_days_per_period
        ),
        "average_hot_days_per_period": _average_or_none(
            hot_days_per_period
        ),
        "data_completeness_percent": completeness,
    }
