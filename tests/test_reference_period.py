from datetime import date

from backend.reference_period import get_latest_complete_reference_period


def test_reference_period_uses_last_five_completed_years_in_2026() -> None:
    period = get_latest_complete_reference_period(as_of=date(2026, 11, 15))

    assert period.start_date == date(2021, 1, 1)
    assert period.end_date == date(2025, 12, 31)
    assert period.last_complete_year == 2025
    assert period.period_days == 1826


def test_reference_period_moves_forward_automatically_in_2027() -> None:
    period = get_latest_complete_reference_period(as_of=date(2027, 1, 1))

    assert period.start_date == date(2022, 1, 1)
    assert period.end_date == date(2026, 12, 31)


def test_reference_period_supports_two_leap_years() -> None:
    period = get_latest_complete_reference_period(as_of=date(2029, 6, 1))

    assert period.start_date == date(2024, 1, 1)
    assert period.end_date == date(2028, 12, 31)
    assert period.period_days == 1827
