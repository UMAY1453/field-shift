import asyncio
from datetime import datetime, timedelta, timezone
import json

import httpx
import pytest

from backend.nasa_service import (
    DEFAULT_DEMO_PATH,
    NASA_DAILY_POINT_URL,
    NASA_PARAMETERS,
    NasaResponseError,
    NasaServiceError,
    build_cache_key,
    build_nasa_request_params,
    fetch_nasa_daily_data,
    fetch_nasa_daily_data_with_retry,
    get_climate_data,
    load_bursa_demo_records,
    normalize_nasa_daily_data,
    read_cache_entry,
    write_cache_entry,
)


def _successful_payload(*, include_enrichment: bool = True) -> dict:
    parameters = {
        "T2M": {"20210101": 5.4},
        "T2M_MIN": {"20210101": 1.8},
        "T2M_MAX": {"20210101": 9.1},
        "PRECTOTCORR": {"20210101": 0},
    }
    if include_enrichment:
        parameters.update(
            {
                "RH2M": {"20210101": 74.2},
                "GWETROOT": {"20210101": 0.61},
            }
        )

    return {"properties": {"parameter": parameters}}


def test_build_request_params_for_one_day_in_bursa() -> None:
    params = build_nasa_request_params(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2021-01-01",
    )

    assert params == {
        "parameters": ",".join(NASA_PARAMETERS),
        "community": "AG",
        "longitude": 29.06,
        "latitude": 40.195,
        "start": "20210101",
        "end": "20210101",
        "format": "JSON",
        "time-standard": "LST",
    }


def test_build_request_params_rejects_invalid_input() -> None:
    with pytest.raises(ValueError):
        build_nasa_request_params(
            latitude=91,
            longitude=29.06,
            start_date="2021-01-01",
            end_date="2021-01-01",
        )

    with pytest.raises(ValueError, match="en fazla 5 yıllık"):
        build_nasa_request_params(
            latitude=40.195,
            longitude=29.06,
            start_date="2020-01-01",
            end_date="2025-12-31",
        )

    with pytest.raises(ValueError):
        build_nasa_request_params(
            latitude=40.195,
            longitude=29.06,
            start_date="2021-01-02",
            end_date="2021-01-01",
        )


@pytest.mark.asyncio
async def test_fetches_successful_raw_response_with_expected_query() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url).startswith(NASA_DAILY_POINT_URL)
        assert request.url.params["parameters"] == ",".join(NASA_PARAMETERS)
        assert request.url.params["community"] == "AG"
        assert request.url.params["time-standard"] == "LST"
        assert request.url.params["start"] == "20210101"
        assert request.url.params["end"] == "20210101"
        return httpx.Response(200, json=_successful_payload())

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        payload = await fetch_nasa_daily_data(
            latitude=40.195,
            longitude=29.06,
            start_date="2021-01-01",
            end_date="2021-01-01",
            client=client,
        )

    assert payload == _successful_payload()


@pytest.mark.asyncio
async def test_optional_enrichment_parameters_may_be_absent() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_successful_payload(include_enrichment=False),
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        payload = await fetch_nasa_daily_data(
            latitude=40.195,
            longitude=29.06,
            start_date="2021-01-01",
            end_date="2021-01-01",
            client=client,
        )

    assert "RH2M" not in payload["properties"]["parameter"]
    assert "GWETROOT" not in payload["properties"]["parameter"]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status_code", "expected_code"),
    [
        (422, "NASA_VALIDATION_ERROR"),
        (429, "NASA_RATE_LIMITED"),
        (503, "NASA_API_UNAVAILABLE"),
    ],
)
async def test_maps_http_errors_to_controlled_errors(
    status_code: int,
    expected_code: str,
) -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code, json={"detail": "error"})

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(NasaServiceError) as error:
            await fetch_nasa_daily_data(
                latitude=40.195,
                longitude=29.06,
                start_date="2021-01-01",
                end_date="2021-01-01",
                client=client,
            )

    assert error.value.code == expected_code
    assert error.value.status_code == status_code


@pytest.mark.asyncio
async def test_maps_timeout_to_controlled_error() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(NasaServiceError) as error:
            await fetch_nasa_daily_data(
                latitude=40.195,
                longitude=29.06,
                start_date="2021-01-01",
                end_date="2021-01-01",
                client=client,
            )

    assert error.value.code == "NASA_REQUEST_TIMEOUT"


@pytest.mark.asyncio
async def test_rejects_invalid_json_response() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            content=b"not-json",
            headers={"content-type": "text/plain"},
        )

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(NasaResponseError) as error:
            await fetch_nasa_daily_data(
                latitude=40.195,
                longitude=29.06,
                start_date="2021-01-01",
                end_date="2021-01-01",
                client=client,
            )

    assert error.value.code == "NASA_INVALID_JSON"


@pytest.mark.asyncio
async def test_rejects_missing_core_parameter() -> None:
    payload = _successful_payload()
    del payload["properties"]["parameter"]["T2M"]

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(
        transport=httpx.MockTransport(handler)
    ) as client:
        with pytest.raises(NasaResponseError) as error:
            await fetch_nasa_daily_data(
                latitude=40.195,
                longitude=29.06,
                start_date="2021-01-01",
                end_date="2021-01-01",
                client=client,
            )

    assert error.value.code == "NASA_MISSING_CORE_PARAMETERS"


def test_normalizes_one_day_response_to_shared_schema() -> None:
    records = normalize_nasa_daily_data(_successful_payload())

    assert records == [
        {
            "date": "2021-01-01",
            "temperature_c": 5.4,
            "temperature_min_c": 1.8,
            "temperature_max_c": 9.1,
            "precipitation_mm": 0.0,
            "relative_humidity_percent": 74.2,
            "root_zone_wetness": 0.61,
        }
    ]


def test_normalization_preserves_zero_and_converts_fill_to_null() -> None:
    payload = _successful_payload()
    payload["header"] = {"fill_value": -999}
    parameters = payload["properties"]["parameter"]
    parameters["T2M"]["20210101"] = -999
    parameters["PRECTOTCORR"]["20210101"] = 0
    parameters["RH2M"]["20210101"] = "invalid"

    record = normalize_nasa_daily_data(payload)[0]

    assert record["temperature_c"] is None
    assert record["precipitation_mm"] == 0
    assert record["relative_humidity_percent"] is None


def test_normalization_allows_missing_enrichment_values() -> None:
    records = normalize_nasa_daily_data(
        _successful_payload(include_enrichment=False)
    )

    assert records[0]["relative_humidity_percent"] is None
    assert records[0]["root_zone_wetness"] is None


def test_normalization_sorts_dates_and_keeps_missing_daily_field_null() -> None:
    payload = _successful_payload()
    parameters = payload["properties"]["parameter"]

    for daily_values in parameters.values():
        daily_values["20210103"] = daily_values["20210101"]
    parameters["T2M"]["20210102"] = 6.2

    records = normalize_nasa_daily_data(payload)

    assert [record["date"] for record in records] == [
        "2021-01-01",
        "2021-01-02",
        "2021-01-03",
    ]
    assert records[1]["temperature_c"] == 6.2
    assert records[1]["precipitation_mm"] is None
    assert records[1]["relative_humidity_percent"] is None


def test_normalization_rejects_invalid_date_key() -> None:
    payload = _successful_payload()
    payload["properties"]["parameter"]["T2M"] = {
        "not-a-date": 5.4
    }

    with pytest.raises(NasaResponseError) as error:
        normalize_nasa_daily_data(payload)

    assert error.value.code == "NASA_INVALID_DATE"


def test_normalization_rejects_empty_daily_data() -> None:
    payload = _successful_payload()
    for parameter in payload["properties"]["parameter"].values():
        parameter.clear()

    with pytest.raises(NasaResponseError) as error:
        normalize_nasa_daily_data(payload)

    assert error.value.code == "NASA_EMPTY_DATA"


def test_cache_key_is_stable_and_request_specific() -> None:
    first = build_cache_key(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2021-01-07",
    )
    same = build_cache_key(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2021-01-07",
    )
    different = build_cache_key(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2021-01-08",
    )

    assert first == same
    assert first != different


def test_writes_and_reads_fresh_cache_entry(tmp_path) -> None:
    cache_key = "test-cache-key"
    now = datetime(2026, 11, 15, tzinfo=timezone.utc)
    records = normalize_nasa_daily_data(_successful_payload())

    write_cache_entry(
        cache_dir=tmp_path,
        cache_key=cache_key,
        request_params={"latitude": 40.195},
        daily_records=records,
        now=now,
    )

    cached = read_cache_entry(
        cache_dir=tmp_path,
        cache_key=cache_key,
        now=now + timedelta(hours=1),
    )

    assert cached == records


def test_ignores_stale_or_corrupt_cache_entry(tmp_path) -> None:
    cache_key = "test-cache-key"
    now = datetime(2026, 11, 15, tzinfo=timezone.utc)
    records = normalize_nasa_daily_data(_successful_payload())

    write_cache_entry(
        cache_dir=tmp_path,
        cache_key=cache_key,
        request_params={"latitude": 40.195},
        daily_records=records,
        now=now - timedelta(days=8),
    )
    assert read_cache_entry(
        cache_dir=tmp_path,
        cache_key=cache_key,
        now=now,
    ) is None

    cache_file = next(tmp_path.glob("*.json"))
    cache_file.write_text("not-json", encoding="utf-8")
    assert read_cache_entry(
        cache_dir=tmp_path,
        cache_key=cache_key,
        now=now,
    ) is None


@pytest.mark.asyncio
async def test_retry_uses_retry_after_then_succeeds() -> None:
    attempts = 0
    delays: list[float] = []

    async def fetcher(**kwargs) -> dict:
        nonlocal attempts
        attempts += 1
        if attempts == 1:
            raise NasaServiceError(
                "NASA_RATE_LIMITED",
                "rate limited",
                status_code=429,
                retry_after_seconds=2,
            )
        return _successful_payload()

    async def fake_sleep(delay: float) -> None:
        delays.append(delay)

    payload = await fetch_nasa_daily_data_with_retry(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2021-01-01",
        fetcher=fetcher,
        sleep=fake_sleep,
    )

    assert payload == _successful_payload()
    assert attempts == 2
    assert delays == [2]


@pytest.mark.asyncio
async def test_retry_does_not_repeat_non_retryable_error() -> None:
    attempts = 0

    async def fetcher(**kwargs) -> dict:
        nonlocal attempts
        attempts += 1
        raise NasaServiceError(
            "NASA_VALIDATION_ERROR",
            "invalid",
            status_code=422,
        )

    async def fake_sleep(delay: float) -> None:
        return None

    with pytest.raises(NasaServiceError) as error:
        await fetch_nasa_daily_data_with_retry(
            latitude=40.195,
            longitude=29.06,
            start_date="2021-01-01",
            end_date="2021-01-01",
            fetcher=fetcher,
            sleep=fake_sleep,
        )

    assert error.value.code == "NASA_VALIDATION_ERROR"
    assert attempts == 1


@pytest.mark.asyncio
async def test_first_request_is_live_and_second_uses_cache(tmp_path) -> None:
    attempts = 0

    async def fetcher(**kwargs) -> dict:
        nonlocal attempts
        attempts += 1
        return _successful_payload()

    first = await get_climate_data(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2021-01-01",
        cache_dir=tmp_path,
        fetcher=fetcher,
    )
    second = await get_climate_data(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2021-01-01",
        cache_dir=tmp_path,
        fetcher=fetcher,
    )

    assert first.mode == "live"
    assert second.mode == "cache"
    assert first.daily_records == second.daily_records
    assert attempts == 1


@pytest.mark.asyncio
async def test_uses_stale_cache_when_nasa_is_unavailable(tmp_path) -> None:
    now = datetime(2026, 11, 15, tzinfo=timezone.utc)
    cache_key = build_cache_key(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2021-01-01",
    )
    records = normalize_nasa_daily_data(_successful_payload())
    write_cache_entry(
        cache_dir=tmp_path,
        cache_key=cache_key,
        request_params={},
        daily_records=records,
        now=now - timedelta(days=8),
    )

    async def failing_fetcher(**kwargs) -> dict:
        raise NasaServiceError(
            "NASA_API_UNAVAILABLE",
            "unavailable",
            status_code=503,
        )

    async def fake_sleep(delay: float) -> None:
        return None

    result = await get_climate_data(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2021-01-01",
        cache_dir=tmp_path,
        fetcher=failing_fetcher,
        sleep=fake_sleep,
        now=now,
    )

    assert result.mode == "cache"
    assert result.daily_records == records
    assert result.warnings


def test_loads_demo_only_for_bursa_and_complete_date_range(tmp_path) -> None:
    demo_path = tmp_path / "demo.json"
    records = normalize_nasa_daily_data(_successful_payload())
    demo_path.write_text(json.dumps(records), encoding="utf-8")

    assert load_bursa_demo_records(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2021-01-01",
        demo_path=demo_path,
    ) == records
    assert load_bursa_demo_records(
        latitude=39.93,
        longitude=32.86,
        start_date="2021-01-01",
        end_date="2021-01-01",
        demo_path=demo_path,
    ) is None


def test_committed_bursa_demo_covers_2021_through_2025() -> None:
    records = load_bursa_demo_records(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2025-12-31",
        demo_path=DEFAULT_DEMO_PATH,
    )

    assert records is not None
    assert len(records) == 1826
    assert records[0]["date"] == "2021-01-01"
    assert records[-1]["date"] == "2025-12-31"
    assert all(
        set(record)
        == {
            "date",
            "temperature_c",
            "temperature_min_c",
            "temperature_max_c",
            "precipitation_mm",
            "relative_humidity_percent",
            "root_zone_wetness",
        }
        for record in records
    )


@pytest.mark.asyncio
async def test_uses_bursa_demo_when_nasa_and_cache_fail(tmp_path) -> None:
    demo_path = tmp_path / "demo.json"
    records = normalize_nasa_daily_data(_successful_payload())
    demo_path.write_text(json.dumps(records), encoding="utf-8")

    async def failing_fetcher(**kwargs) -> dict:
        raise NasaServiceError(
            "NASA_API_UNAVAILABLE",
            "unavailable",
            status_code=503,
        )

    async def fake_sleep(delay: float) -> None:
        return None

    result = await get_climate_data(
        latitude=40.195,
        longitude=29.06,
        start_date="2021-01-01",
        end_date="2021-01-01",
        cache_dir=tmp_path / "cache",
        demo_path=demo_path,
        fetcher=failing_fetcher,
        sleep=fake_sleep,
    )

    assert result.mode == "demo"
    assert result.daily_records == records
    assert result.warnings


@pytest.mark.asyncio
async def test_concurrent_identical_requests_share_one_nasa_call(tmp_path) -> None:
    attempts = 0

    async def fetcher(**kwargs) -> dict:
        nonlocal attempts
        attempts += 1
        await asyncio.sleep(0.01)
        return _successful_payload()

    results = await asyncio.gather(
        *[
            get_climate_data(
                latitude=40.195,
                longitude=29.06,
                start_date="2021-01-01",
                end_date="2021-01-01",
                cache_dir=tmp_path,
                fetcher=fetcher,
            )
            for _ in range(5)
        ]
    )

    assert attempts == 1
    assert all(result.mode == "live" for result in results)
    assert all(
        result.daily_records == results[0].daily_records
        for result in results
    )


@pytest.mark.asyncio
async def test_rejects_live_response_with_missing_requested_day(tmp_path) -> None:
    async def fetcher(**kwargs) -> dict:
        return _successful_payload()

    with pytest.raises(NasaResponseError) as error:
        await get_climate_data(
            latitude=40.195,
            longitude=29.06,
            start_date="2021-01-01",
            end_date="2021-01-02",
            cache_dir=tmp_path,
            demo_path=tmp_path / "missing-demo.json",
            fetcher=fetcher,
        )

    assert error.value.code == "NASA_INCOMPLETE_DATE_RANGE"


@pytest.mark.asyncio
async def test_validation_error_does_not_fall_back_to_demo(tmp_path) -> None:
    demo_path = tmp_path / "demo.json"
    records = normalize_nasa_daily_data(_successful_payload())
    demo_path.write_text(json.dumps(records), encoding="utf-8")

    async def invalid_fetcher(**kwargs) -> dict:
        raise NasaServiceError(
            "NASA_VALIDATION_ERROR",
            "invalid request",
            status_code=422,
        )

    with pytest.raises(NasaServiceError) as error:
        await get_climate_data(
            latitude=40.195,
            longitude=29.06,
            start_date="2021-01-01",
            end_date="2021-01-01",
            cache_dir=tmp_path / "cache",
            demo_path=demo_path,
            fetcher=invalid_fetcher,
        )

    assert error.value.code == "NASA_VALIDATION_ERROR"
