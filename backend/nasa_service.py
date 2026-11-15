"""NASA POWER Daily API istemcisi.

Bu ilk aşama yalnızca ham günlük JSON cevabını güvenli biçimde alır ve cevabın
temel yapısını doğrular. Normalizasyon, retry, cache ve demo fallback sonraki
aşamalarda eklenecektir.
"""

from __future__ import annotations

from datetime import date
import math
from typing import Any

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
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class NasaResponseError(NasaServiceError):
    """NASA cevabı JSON olsa bile beklenen yapıyı taşımadığında oluşur."""


def _parse_date(value: date | str, field_name: str) -> date:
    if isinstance(value, date):
        return value

    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as exc:
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
        raise NasaServiceError(
            "NASA_RATE_LIMITED",
            "NASA POWER çok fazla istek nedeniyle isteği sınırlandırdı.",
            status_code=429,
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
