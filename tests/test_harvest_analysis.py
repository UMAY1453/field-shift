from datetime import date, timedelta

import pytest

from backend.harvest_analysis import (
    HarvestAnalysisError,
    analyze_harvest_period,
)


def _records_for_periods(
    *,
    start_month: int,
    start_day: int,
    period_days: int,
    years: range,
) -> list[dict]:
    records = []
    for year in years:
        period_start = date(year, start_month, start_day)
        for offset in range(period_days):
            record_date = period_start + timedelta(days=offset)
            records.append(
                {
                    "date": record_date.isoformat(),
                    "temperature_c": 20.0 + offset,
                    "temperature_min_c": 15.0,
                    "temperature_max_c": 34.0 + offset,
                    "precipitation_mm": float(offset),
                    "relative_humidity_percent": 60.0,
                    "root_zone_wetness": 0.5,
                }
            )
    return records


def test_analyzes_same_harvest_window_across_historical_years() -> None:
    records = _records_for_periods(
        start_month=8,
        start_day=15,
        period_days=3,
        years=range(2021, 2026),
    )

    result = analyze_harvest_period(
        records,
        harvest_start_date=date(2027, 8, 15),
        harvest_end_date=date(2027, 8, 17),
    )

    assert result["period_days"] == 3
    assert result["seasons_analyzed"] == 5
    assert result["average_temperature_c"] == 21.0
    assert result["average_maximum_temperature_c"] == 35.0
    assert result["average_precipitation_mm_per_period"] == 3.0
    assert result["average_rainy_days_per_period"] == 2.0
    assert result["average_hot_days_per_period"] == 2.0
    assert result["data_completeness_percent"] == 100.0


def test_supports_harvest_period_crossing_new_year() -> None:
    records = _records_for_periods(
        start_month=12,
        start_day=30,
        period_days=4,
        years=range(2021, 2025),
    )

    result = analyze_harvest_period(
        records,
        harvest_start_date=date(2027, 12, 30),
        harvest_end_date=date(2028, 1, 2),
    )

    assert result["period_days"] == 4
    assert result["seasons_analyzed"] == 4
    assert result["historical_windows"][0] == {
        "start_date": "2021-12-30",
        "end_date": "2022-01-02",
    }


def test_reports_incomplete_measurements_without_treating_zero_as_missing() -> None:
    records = _records_for_periods(
        start_month=8,
        start_day=15,
        period_days=2,
        years=range(2021, 2023),
    )
    records[0]["temperature_c"] = None
    records[1]["precipitation_mm"] = 0.0

    result = analyze_harvest_period(
        records,
        harvest_start_date=date(2027, 8, 15),
        harvest_end_date=date(2027, 8, 16),
    )

    assert result["data_completeness_percent"] == 91.7
    assert result["average_precipitation_mm_per_period"] == 0.5


def test_rejects_missing_historical_window() -> None:
    with pytest.raises(HarvestAnalysisError, match="günlük iklim kaydı"):
        analyze_harvest_period(
            [],
            harvest_start_date=date(2027, 8, 15),
            harvest_end_date=date(2027, 8, 17),
        )


def test_rejects_duplicate_dates() -> None:
    records = _records_for_periods(
        start_month=8,
        start_day=15,
        period_days=1,
        years=range(2021, 2022),
    )
    records.append(dict(records[0]))

    with pytest.raises(HarvestAnalysisError, match="tekrarlı"):
        analyze_harvest_period(
            records,
            harvest_start_date=date(2027, 8, 15),
            harvest_end_date=date(2027, 8, 15),
        )
