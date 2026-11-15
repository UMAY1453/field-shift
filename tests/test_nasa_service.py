import httpx
import pytest

from backend.nasa_service import (
    NASA_DAILY_POINT_URL,
    NASA_PARAMETERS,
    NasaResponseError,
    NasaServiceError,
    build_nasa_request_params,
    fetch_nasa_daily_data,
    normalize_nasa_daily_data,
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
