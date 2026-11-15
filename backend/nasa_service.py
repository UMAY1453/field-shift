"""NASA POWER günlük verisini alma, normalleştirme ve dayanıklılık katmanı."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import random
from typing import Any, Literal
from uuid import uuid4

import httpx


NASA_DAILY_POINT_URL = (
    "https://power.larc.nasa.gov/api/temporal/daily/point"
)

CORE_PARAMETERS = (
    "T2M",
    "T2M_MIN",
    "T2M_MAX",
    "PRECTOTCORR",
)

ENRICHMENT_PARAMETERS = (
    "RH2M",
    "GWETROOT",
)

NASA_PARAMETERS = CORE_PARAMETERS + ENRICHMENT_PARAMETERS
NASA_COMMUNITY = "AG"
NASA_FORMAT = "JSON"
NASA_TIME_STANDARD = "LST"
NASA_TIMEOUT_SECONDS = 30.0
NASA_DEFAULT_FILL_VALUE = -999.0
MAX_DATE_RANGE_DAYS = 1827
NASA_MAX_ATTEMPTS = 3
NASA_MAX_BACKOFF_SECONDS = 8.0
NASA_MAX_RETRY_AFTER_SECONDS = 10.0
NASA_TOTAL_RETRY_BUDGET_SECONDS = 35.0
NASA_MAX_CONCURRENT_REQUESTS = 4
CACHE_VERSION = 1
CACHE_MAX_AGE_SECONDS = 7 * 24 * 60 * 60

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CACHE_DIR = PROJECT_ROOT / "backend" / "cache"
DEFAULT_DEMO_PATH = PROJECT_ROOT / "backend" / "data" / "demo_climate.json"

BURSA_DEMO_LATITUDE = 40.195
BURSA_DEMO_LONGITUDE = 29.06
BURSA_DEMO_COORDINATE_TOLERANCE = 0.01
BURSA_DEMO_START_DATE = date(2021, 1, 1)
BURSA_DEMO_END_DATE = date(2025, 12, 31)

RETRYABLE_ERROR_CODES = {
    "NASA_RATE_LIMITED",
    "NASA_API_UNAVAILABLE",
    "NASA_REQUEST_TIMEOUT",
    "NASA_CONNECTION_ERROR",
}

_NASA_REQUEST_SEMAPHORE = asyncio.Semaphore(NASA_MAX_CONCURRENT_REQUESTS)
_IN_FLIGHT_REQUESTS: dict[
    tuple[str, str, str, str],
    asyncio.Task[ClimateDataResult],
] = {}

NORMALIZED_FIELD_BY_PARAMETER = {
    "T2M": "temperature_c",
    "T2M_MIN": "temperature_min_c",
    "T2M_MAX": "temperature_max_c",
    "PRECTOTCORR": "precipitation_mm",
    "RH2M": "relative_humidity_percent",
    "GWETROOT": "root_zone_wetness",
}


class NasaServiceError(RuntimeError):
    """NASA veri katmanındaki kontrollü hataların ortak sınıfı."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        status_code: int | None = None,
        retry_after_seconds: float | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.retry_after_seconds = retry_after_seconds


class NasaResponseError(NasaServiceError):
    """NASA cevabı JSON olsa bile beklenen yapıyı taşımadığında oluşur."""


@dataclass(slots=True)
class ClimateDataResult:
    """Analiz modülüne verilecek günlük kayıtlar ve veri kaynağı bilgisi."""

    daily_records: list[dict[str, Any]]
    mode: Literal["live", "cache", "demo"]
    warnings: list[str] = field(default_factory=list)
    cache_key: str | None = None
    start_date: date | None = None
    end_date: date | None = None
    fallback_used: bool = False


def _parse_date(value: object, field_name: str) -> date:
    if isinstance(value, date):
        return value

    if not isinstance(value, str):
        raise ValueError(
            f"{field_name} YYYY-MM-DD biçiminde geçerli bir tarih olmalıdır."
        )

    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(
            f"{field_name} YYYY-MM-DD biçiminde geçerli bir tarih olmalıdır."
        ) from exc


def build_nasa_request_params(
    *,
    latitude: float,
    longitude: float,
    start_date: date | str,
    end_date: date | str,
) -> dict[str, str | float]:
    """Uygulama girdilerini NASA POWER query parametrelerine dönüştürür."""

    if not -90 <= latitude <= 90:
        raise ValueError("latitude -90 ile 90 arasında olmalıdır.")
    if not -180 <= longitude <= 180:
        raise ValueError("longitude -180 ile 180 arasında olmalıdır.")

    parsed_start = _parse_date(start_date, "start_date")
    parsed_end = _parse_date(end_date, "end_date")

    if parsed_start > parsed_end:
        raise ValueError(
            "Başlangıç tarihi, bitiş tarihinden sonra olamaz."
        )
    requested_days = (parsed_end - parsed_start).days + 1
    if requested_days > MAX_DATE_RANGE_DAYS:
        raise ValueError("Tek istekte en fazla 5 yıllık veri alınabilir.")

    return {
        "parameters": ",".join(NASA_PARAMETERS),
        "community": NASA_COMMUNITY,
        "longitude": longitude,
        "latitude": latitude,
        "start": parsed_start.strftime("%Y%m%d"),
        "end": parsed_end.strftime("%Y%m%d"),
        "format": NASA_FORMAT,
        "time-standard": NASA_TIME_STANDARD,
    }


def extract_parameter_data(payload: dict[str, Any]) -> dict[str, Any]:
    """Ham cevap içinden parametre sözlüğünü alır ve çekirdek alanları doğrular."""

    properties = payload.get("properties")
    if not isinstance(properties, dict):
        raise NasaResponseError(
            "NASA_INVALID_RESPONSE",
            "NASA POWER cevabında properties alanı bulunamadı.",
        )

    parameter_data = properties.get("parameter")
    if not isinstance(parameter_data, dict):
        raise NasaResponseError(
            "NASA_INVALID_RESPONSE",
            "NASA POWER cevabında parameter alanı bulunamadı.",
        )

    missing_core = [
        parameter
        for parameter in CORE_PARAMETERS
        if not isinstance(parameter_data.get(parameter), dict)
    ]
    if missing_core:
        raise NasaResponseError(
            "NASA_MISSING_CORE_PARAMETERS",
            "NASA POWER cevabında çekirdek parametreler eksik: "
            + ", ".join(missing_core),
        )

    return parameter_data


def _get_fill_value(payload: dict[str, Any]) -> float:
    header = payload.get("header")
    if isinstance(header, dict):
        fill_value = header.get("fill_value")
        if isinstance(fill_value, (int, float)) and not isinstance(
            fill_value, bool
        ):
            return float(fill_value)
    return NASA_DEFAULT_FILL_VALUE


def _normalize_numeric_value(
    value: Any,
    *,
    fill_value: float,
) -> float | None:
    """NASA sayısal değerini JSON uyumlu sayı veya null'a dönüştürür."""

    if value is None or isinstance(value, bool):
        return None
    if not isinstance(value, (int, float)):
        return None

    normalized = float(value)
    if not math.isfinite(normalized):
        return None
    if normalized == fill_value or normalized == NASA_DEFAULT_FILL_VALUE:
        return None
    return normalized


def normalize_nasa_daily_data(
    payload: dict[str, Any],
) -> list[dict[str, Any]]:
    """Ham NASA JSON'unu tarihe göre sıralı ortak günlük kayıtlara çevirir."""

    parameter_data = extract_parameter_data(payload)
    fill_value = _get_fill_value(payload)

    date_keys: set[str] = set()
    for parameter in NASA_PARAMETERS:
        daily_values = parameter_data.get(parameter)
        if isinstance(daily_values, dict):
            date_keys.update(str(key) for key in daily_values)

    if not date_keys:
        raise NasaResponseError(
            "NASA_EMPTY_DATA",
            "NASA POWER cevabında günlük veri bulunamadı.",
        )

    parsed_dates: list[tuple[date, str]] = []
    for date_key in date_keys:
        try:
            parsed_date = date.fromisoformat(
                f"{date_key[0:4]}-{date_key[4:6]}-{date_key[6:8]}"
            )
        except (TypeError, ValueError) as exc:
            raise NasaResponseError(
                "NASA_INVALID_DATE",
                f"NASA POWER cevabında geçersiz tarih anahtarı var: {date_key}",
            ) from exc

        if len(date_key) != 8 or not date_key.isdigit():
            raise NasaResponseError(
                "NASA_INVALID_DATE",
                f"NASA POWER cevabında geçersiz tarih anahtarı var: {date_key}",
            )
        parsed_dates.append((parsed_date, date_key))

    records: list[dict[str, Any]] = []
    for parsed_date, date_key in sorted(parsed_dates):
        record: dict[str, Any] = {
            "date": parsed_date.isoformat(),
        }
        for parameter, field_name in NORMALIZED_FIELD_BY_PARAMETER.items():
            daily_values = parameter_data.get(parameter)
            raw_value = (
                daily_values.get(date_key)
                if isinstance(daily_values, dict)
                else None
            )
            record[field_name] = _normalize_numeric_value(
                raw_value,
                fill_value=fill_value,
            )
        records.append(record)

    return records


def _raise_for_http_status(response: httpx.Response) -> None:
    if response.status_code == 422:
        raise NasaServiceError(
            "NASA_VALIDATION_ERROR",
            "NASA POWER isteği parametre doğrulamasından geçemedi.",
            status_code=422,
        )
    if response.status_code == 429:
        retry_after: float | None = None
        raw_retry_after = response.headers.get("retry-after")
        if raw_retry_after is not None:
            try:
                retry_after = max(0.0, float(raw_retry_after))
            except ValueError:
                retry_after = None
        raise NasaServiceError(
            "NASA_RATE_LIMITED",
            "NASA POWER çok fazla istek nedeniyle isteği sınırlandırdı.",
            status_code=429,
            retry_after_seconds=retry_after,
        )
    if response.status_code >= 500:
        raise NasaServiceError(
            "NASA_API_UNAVAILABLE",
            "NASA POWER servisi geçici olarak kullanılamıyor.",
            status_code=response.status_code,
        )
    if response.status_code != 200:
        raise NasaServiceError(
            "NASA_API_ERROR",
            f"NASA POWER beklenmeyen HTTP {response.status_code} cevabı döndürdü.",
            status_code=response.status_code,
        )


async def fetch_nasa_daily_data(
    *,
    latitude: float,
    longitude: float,
    start_date: date | str,
    end_date: date | str,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Tek nokta için NASA POWER ham günlük JSON cevabını döndürür."""

    params = build_nasa_request_params(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
    )

    owns_client = client is None
    active_client = client or httpx.AsyncClient(
        timeout=NASA_TIMEOUT_SECONDS,
        follow_redirects=True,
    )

    try:
        try:
            response = await active_client.get(
                NASA_DAILY_POINT_URL,
                params=params,
            )
        except httpx.TimeoutException as exc:
            raise NasaServiceError(
                "NASA_REQUEST_TIMEOUT",
                "NASA POWER isteği zaman aşımına uğradı.",
            ) from exc
        except httpx.RequestError as exc:
            raise NasaServiceError(
                "NASA_CONNECTION_ERROR",
                "NASA POWER servisine bağlanılamadı.",
            ) from exc

        _raise_for_http_status(response)

        try:
            payload = response.json()
        except ValueError as exc:
            raise NasaResponseError(
                "NASA_INVALID_JSON",
                "NASA POWER geçerli bir JSON cevabı döndürmedi.",
            ) from exc

        if not isinstance(payload, dict):
            raise NasaResponseError(
                "NASA_INVALID_RESPONSE",
                "NASA POWER JSON cevabının kök yapısı nesne olmalıdır.",
            )

        # Bu aşamada çekirdek alanlar zorunlu, RH2M ve GWETROOT zenginleştirici
        # alanlardır. Zenginleştirici alanların yokluğu ham isteği başarısız
        # saymaz; normalizasyon aşamasında null olarak ele alınacaktır.
        extract_parameter_data(payload)
        return payload
    finally:
        if owns_client:
            await active_client.aclose()


NasaFetcher = Callable[..., Awaitable[dict[str, Any]]]
SleepFunction = Callable[[float], Awaitable[None]]


async def fetch_nasa_daily_data_with_retry(
    *,
    latitude: float,
    longitude: float,
    start_date: date | str,
    end_date: date | str,
    client: httpx.AsyncClient | None = None,
    fetcher: NasaFetcher | None = None,
    sleep: SleepFunction = asyncio.sleep,
    max_attempts: int = NASA_MAX_ATTEMPTS,
) -> dict[str, Any]:
    """Geçici NASA hatalarında sınırlı ve artan beklemeli yeniden deneme yapar."""

    if max_attempts < 1:
        raise ValueError("max_attempts en az 1 olmalıdır.")

    active_fetcher = fetcher or fetch_nasa_daily_data

    for attempt in range(1, max_attempts + 1):
        try:
            return await active_fetcher(
                latitude=latitude,
                longitude=longitude,
                start_date=start_date,
                end_date=end_date,
                client=client,
            )
        except NasaServiceError as exc:
            is_last_attempt = attempt == max_attempts
            if exc.code not in RETRYABLE_ERROR_CODES or is_last_attempt:
                raise

            exponential_delay = min(
                2 ** (attempt - 1),
                NASA_MAX_BACKOFF_SECONDS,
            )
            delay = (
                min(
                    exc.retry_after_seconds,
                    NASA_MAX_RETRY_AFTER_SECONDS,
                )
                if exc.retry_after_seconds is not None
                else exponential_delay + random.uniform(0, 0.25)
            )
            await sleep(delay)

    raise AssertionError("Retry döngüsü beklenmeyen biçimde tamamlandı.")


def build_cache_key(
    *,
    latitude: float,
    longitude: float,
    start_date: date | str,
    end_date: date | str,
) -> str:
    """NASA isteğinin bütün veri belirleyici alanlarından kararlı anahtar üretir."""

    params = build_nasa_request_params(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
    )
    canonical = json.dumps(
        params,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _cache_file_path(cache_dir: Path, cache_key: str) -> Path:
    return cache_dir / f"{cache_key}.json"


def write_cache_entry(
    *,
    cache_dir: Path,
    cache_key: str,
    request_params: dict[str, str | float],
    daily_records: list[dict[str, Any]],
    now: datetime | None = None,
) -> None:
    """Normalize kayıtları geçici dosya üzerinden atomik biçimde cache'e yazar."""

    created_at = now or datetime.now(timezone.utc)
    cache_dir.mkdir(parents=True, exist_ok=True)
    target_path = _cache_file_path(cache_dir, cache_key)
    temporary_path = cache_dir / f".{cache_key}.{uuid4().hex}.tmp"
    payload = {
        "version": CACHE_VERSION,
        "created_at": created_at.isoformat(),
        "request": request_params,
        "daily_records": daily_records,
    }

    try:
        temporary_path.write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        temporary_path.replace(target_path)
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


def read_cache_entry(
    *,
    cache_dir: Path,
    cache_key: str,
    max_age_seconds: float | None = CACHE_MAX_AGE_SECONDS,
    now: datetime | None = None,
) -> list[dict[str, Any]] | None:
    """Geçerli cache kaydını döndürür; bozuk veya süresi geçmiş kaydı yok sayar."""

    path = _cache_file_path(cache_dir, cache_key)
    if not path.is_file():
        return None

    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("version") != CACHE_VERSION:
            return None
        records = payload.get("daily_records")
        if not isinstance(records, list) or not all(
            isinstance(record, dict) for record in records
        ):
            return None
        created_at = datetime.fromisoformat(payload["created_at"])
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)
    except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError):
        return None

    if max_age_seconds is not None:
        current_time = now or datetime.now(timezone.utc)
        age_seconds = (current_time - created_at).total_seconds()
        if age_seconds < 0 or age_seconds > max_age_seconds:
            return None

    return records


def _records_cover_date_range(
    records: list[dict[str, Any]],
    *,
    start_date: date | str,
    end_date: date | str,
) -> bool:
    """Kayıtların istenen her günü bir kez içerdiğini doğrular."""

    parsed_start = _parse_date(start_date, "start_date")
    parsed_end = _parse_date(end_date, "end_date")
    expected_days = (parsed_end - parsed_start).days + 1
    expected_dates = {
        (parsed_start + timedelta(days=offset)).isoformat()
        for offset in range(expected_days)
    }

    record_dates: list[str] = []
    for record in records:
        raw_date = record.get("date")
        try:
            normalized_date = _parse_date(raw_date, "date").isoformat()
        except ValueError:
            return False
        record_dates.append(normalized_date)

    return (
        len(record_dates) == expected_days
        and len(set(record_dates)) == expected_days
        and set(record_dates) == expected_dates
    )


def load_bursa_demo_records(
    *,
    latitude: float,
    longitude: float,
    start_date: date | str,
    end_date: date | str,
    demo_path: Path = DEFAULT_DEMO_PATH,
) -> list[dict[str, Any]] | None:
    """Yalnızca Bursa ve demo döneminin kapsadığı tarihler için kayıt döndürür."""

    if (
        abs(latitude - BURSA_DEMO_LATITUDE)
        > BURSA_DEMO_COORDINATE_TOLERANCE
        or abs(longitude - BURSA_DEMO_LONGITUDE)
        > BURSA_DEMO_COORDINATE_TOLERANCE
    ):
        return None

    parsed_start = _parse_date(start_date, "start_date")
    parsed_end = _parse_date(end_date, "end_date")

    try:
        payload = json.loads(demo_path.read_text(encoding="utf-8"))
    except (OSError, ValueError, json.JSONDecodeError):
        return None
    if not isinstance(payload, list):
        return None

    selected: list[dict[str, Any]] = []
    for record in payload:
        if not isinstance(record, dict):
            return None
        raw_date = record.get("date")
        try:
            record_date = _parse_date(raw_date, "date")
        except ValueError:
            return None
        if parsed_start <= record_date <= parsed_end:
            selected.append(record)

    selected.sort(key=lambda record: record["date"])
    if not _records_cover_date_range(
        selected,
        start_date=parsed_start,
        end_date=parsed_end,
    ):
        return None
    return selected


async def _fetch_with_fallbacks(
    *,
    latitude: float,
    longitude: float,
    start_date: date | str,
    end_date: date | str,
    cache_dir: Path,
    demo_path: Path,
    cache_key: str,
    request_params: dict[str, str | float],
    fetcher: NasaFetcher | None,
    sleep: SleepFunction,
    now: datetime | None,
    allow_verified_bursa_fallback: bool,
) -> ClimateDataResult:
    """Canlı isteği yapar; başarısızlıkta eski cache ve demoyu dener."""

    try:
        try:
            async with asyncio.timeout(NASA_TOTAL_RETRY_BUDGET_SECONDS):
                async with _NASA_REQUEST_SEMAPHORE:
                    raw_payload = await fetch_nasa_daily_data_with_retry(
                        latitude=latitude,
                        longitude=longitude,
                        start_date=start_date,
                        end_date=end_date,
                        fetcher=fetcher,
                        sleep=sleep,
                    )
        except TimeoutError as exc:
            raise NasaServiceError(
                "NASA_REQUEST_TIMEOUT",
                "NASA POWER toplam deneme süresi aşıldı.",
            ) from exc
        records = normalize_nasa_daily_data(raw_payload)
        if not _records_cover_date_range(
            records,
            start_date=start_date,
            end_date=end_date,
        ):
            raise NasaResponseError(
                "NASA_INCOMPLETE_DATE_RANGE",
                "NASA POWER cevabı istenen tarih aralığının tüm günlerini içermiyor.",
            )

        warnings: list[str] = []
        try:
            await asyncio.to_thread(
                write_cache_entry,
                cache_dir=cache_dir,
                cache_key=cache_key,
                request_params=request_params,
                daily_records=records,
                now=now,
            )
        except OSError:
            warnings.append("NASA verisi alındı ancak cache'e yazılamadı.")

        return ClimateDataResult(
            daily_records=records,
            mode="live",
            warnings=warnings,
            cache_key=cache_key,
            start_date=_parse_date(start_date, "start_date"),
            end_date=_parse_date(end_date, "end_date"),
        )
    except NasaServiceError as nasa_error:
        if nasa_error.code in {
            "NASA_VALIDATION_ERROR",
            "NASA_API_ERROR",
        }:
            raise

        stale_records = await asyncio.to_thread(
            read_cache_entry,
            cache_dir=cache_dir,
            cache_key=cache_key,
            max_age_seconds=None,
            now=now,
        )
        if stale_records is not None and _records_cover_date_range(
            stale_records,
            start_date=start_date,
            end_date=end_date,
        ):
            return ClimateDataResult(
                daily_records=stale_records,
                mode="cache",
                warnings=[
                    "NASA POWER kullanılamadığı için eski cache verisi kullanıldı."
                ],
                cache_key=cache_key,
                start_date=_parse_date(start_date, "start_date"),
                end_date=_parse_date(end_date, "end_date"),
            )

        demo_records = await asyncio.to_thread(
            load_bursa_demo_records,
            latitude=latitude,
            longitude=longitude,
            start_date=start_date,
            end_date=end_date,
            demo_path=demo_path,
        )
        if demo_records is not None:
            return ClimateDataResult(
                daily_records=demo_records,
                mode="demo",
                warnings=[
                    "NASA POWER kullanılamadığı için Bursa demo verisi kullanıldı."
                ],
                cache_key=cache_key,
                start_date=_parse_date(start_date, "start_date"),
                end_date=_parse_date(end_date, "end_date"),
            )

        if allow_verified_bursa_fallback:
            verified_records = await asyncio.to_thread(
                load_bursa_demo_records,
                latitude=latitude,
                longitude=longitude,
                start_date=BURSA_DEMO_START_DATE,
                end_date=BURSA_DEMO_END_DATE,
                demo_path=demo_path,
            )
            if verified_records is not None:
                requested_start = _parse_date(start_date, "start_date")
                requested_end = _parse_date(end_date, "end_date")
                return ClimateDataResult(
                    daily_records=verified_records,
                    mode="demo",
                    warnings=[
                        f"İstenen {requested_start.isoformat()}–"
                        f"{requested_end.isoformat()} dönemi alınamadı; "
                        "Bursa için doğrulanmış 2021-01-01–2025-12-31 "
                        "dönemi kullanıldı."
                    ],
                    cache_key=cache_key,
                    start_date=BURSA_DEMO_START_DATE,
                    end_date=BURSA_DEMO_END_DATE,
                    fallback_used=True,
                )

        raise nasa_error


async def get_climate_data(
    *,
    latitude: float,
    longitude: float,
    start_date: date | str,
    end_date: date | str,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    demo_path: Path = DEFAULT_DEMO_PATH,
    fetcher: NasaFetcher | None = None,
    sleep: SleepFunction = asyncio.sleep,
    now: datetime | None = None,
    allow_verified_bursa_fallback: bool = False,
) -> ClimateDataResult:
    """Cache, hazır Bursa verisi, canlı NASA ve fallback sırasını yönetir."""

    request_params = build_nasa_request_params(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
    )
    cache_key = build_cache_key(
        latitude=latitude,
        longitude=longitude,
        start_date=start_date,
        end_date=end_date,
    )

    fresh_records = await asyncio.to_thread(
        read_cache_entry,
        cache_dir=cache_dir,
        cache_key=cache_key,
        now=now,
    )
    if fresh_records is not None and _records_cover_date_range(
        fresh_records,
        start_date=start_date,
        end_date=end_date,
    ):
        return ClimateDataResult(
            daily_records=fresh_records,
            mode="cache",
            cache_key=cache_key,
            start_date=_parse_date(start_date, "start_date"),
            end_date=_parse_date(end_date, "end_date"),
        )

    parsed_start = _parse_date(start_date, "start_date")
    parsed_end = _parse_date(end_date, "end_date")
    if (
        parsed_start == BURSA_DEMO_START_DATE
        and parsed_end == BURSA_DEMO_END_DATE
    ):
        bundled_records = await asyncio.to_thread(
            load_bursa_demo_records,
            latitude=latitude,
            longitude=longitude,
            start_date=parsed_start,
            end_date=parsed_end,
            demo_path=demo_path,
        )
        if bundled_records is not None:
            return ClimateDataResult(
                daily_records=bundled_records,
                mode="demo",
                warnings=[
                    "Bursa 2021-2025 için repoyla birlikte sunulan "
                    "hazır tarihsel veri kullanıldı."
                ],
                cache_key=cache_key,
                start_date=parsed_start,
                end_date=parsed_end,
            )

    flight_key = (
        cache_key,
        str(cache_dir.resolve()),
        str(demo_path.resolve()),
        str(allow_verified_bursa_fallback),
    )
    task = _IN_FLIGHT_REQUESTS.get(flight_key)
    if task is None:
        task = asyncio.create_task(
            _fetch_with_fallbacks(
                latitude=latitude,
                longitude=longitude,
                start_date=start_date,
                end_date=end_date,
                cache_dir=cache_dir,
                demo_path=demo_path,
                cache_key=cache_key,
                request_params=request_params,
                fetcher=fetcher,
                sleep=sleep,
                now=now,
                allow_verified_bursa_fallback=allow_verified_bursa_fallback,
            )
        )
        _IN_FLIGHT_REQUESTS[flight_key] = task

    try:
        return await asyncio.shield(task)
    finally:
        if task.done() and _IN_FLIGHT_REQUESTS.get(flight_key) is task:
            _IN_FLIGHT_REQUESTS.pop(flight_key, None)
