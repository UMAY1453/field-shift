"""İklim analizi için kayan tarihsel referans dönemini belirler."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


REFERENCE_PERIOD_YEARS = 5


@dataclass(frozen=True, slots=True)
class ReferencePeriod:
    """Tamamlanmış takvim yıllarından oluşan tarih aralığı."""

    start_date: date
    end_date: date

    @property
    def last_complete_year(self) -> int:
        return self.end_date.year

    @property
    def period_days(self) -> int:
        return (self.end_date - self.start_date).days + 1


def get_latest_complete_reference_period(
    *,
    as_of: date | None = None,
) -> ReferencePeriod:
    """Verilen güne göre son beş tamamlanmış takvim yılını döndürür."""

    current_date = as_of or date.today()
    last_complete_year = current_date.year - 1
    first_year = last_complete_year - REFERENCE_PERIOD_YEARS + 1
    return ReferencePeriod(
        start_date=date(first_year, 1, 1),
        end_date=date(last_complete_year, 12, 31),
    )


def default_reference_start_date() -> date:
    return get_latest_complete_reference_period().start_date


def default_reference_end_date() -> date:
    return get_latest_complete_reference_period().end_date
