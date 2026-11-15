# Field Shift - Technical Contracts

## 1. Purpose

This document defines the shared data contracts between the browser interface, FastAPI application, NASA POWER data layer, climate analysis, historical harvest-window analysis, and crop-rotation recommendation engine.

Public field names and structures must not change without updating the affected modules, tests, and this document.

## 2. General Rules

- The API accepts and returns JSON.
- JSON field names use `snake_case`.
- Dates use the ISO `YYYY-MM-DD` format.
- Temperatures use degrees Celsius (`°C`).
- Precipitation uses millimetres (`mm`).
- Scores use the inclusive `0-100` range.
- Missing numeric climate measurements are represented by `null`.
- Boolean values are never accepted as numbers.
- `NaN`, positive infinity, and negative infinity are rejected.
- A real numeric `0` is valid data and is not treated as missing.
- User-facing explanations must distinguish evidence, assumptions, and limitations.
- Results must be presented as decision support, not as guaranteed agronomic advice or a weather forecast.
- Unknown request fields are rejected.

## 3. Application Addresses

### Production

```text
https://field-shift-mocha-sigma.vercel.app
```

The production deployment serves the frontend and API from the same origin.

### Local development

```text
http://127.0.0.1:8000
```

Run the local application with:

```powershell
python -m uvicorn backend.main:app --reload
```

All API routes begin with `/api`. FastAPI also serves the frontend from `/`, so a separate frontend server is not required. Ports `5500` on `localhost` and `127.0.0.1` remain allowed by CORS for optional frontend-only development.

## 4. Health Endpoint

### Request

```http
GET /api/health
```

### Successful response

```json
{
  "status": "ok",
  "service": "field-shift-api"
}
```

The endpoint verifies that the FastAPI application can respond. It does not perform a NASA POWER request.

## 5. Crop Catalogue Endpoint

### Request

```http
GET /api/crops
```

### Successful response shape

```json
{
  "crops": [
    {
      "id": "wheat",
      "name": "Buğday",
      "family": "Poaceae",
      "is_legume": false,
      "growing_season": ["autumn", "winter"],
      "water_need": "medium",
      "suitable_soils": ["loamy", "clay"],
      "soil_notes": [],
      "temperature_range_c": {
        "min": 10,
        "max": 24
      },
      "absolute_temperature_range_c": {
        "min": 3,
        "max": 32
      },
      "temperature_notes": [],
      "annual_precipitation_range_mm": {
        "min": 350,
        "max": 900
      },
      "rotation": {
        "minimum_return_years": 2,
        "avoid_continuous_cropping": true,
        "example_rotations": [["wheat", "chickpea"]],
        "disease_groups": [],
        "notes": []
      },
      "sources": [
        {
          "title": "Source title",
          "url": "https://example.org/source",
          "supports": ["temperature_range_c"]
        }
      ]
    }
  ]
}
```

Unlike an earlier lightweight draft, the final endpoint returns the validated full crop objects used by the application.

### Crop object fields

| Field | Type | Contract |
|---|---|---|
| `id` | string | Unique API identifier |
| `name` | string | Localized display name |
| `family` | string | Botanical family |
| `is_legume` | boolean | Whether the crop is a legume |
| `growing_season` | string[] | One or more of `spring`, `summer`, `autumn`, `winter` |
| `water_need` | string | `low`, `medium`, or `high` |
| `suitable_soils` | string[] | One or more supported soil identifiers |
| `soil_notes` | string[] | Source-supported drainage and soil notes |
| `temperature_range_c` | object | General optimum range with finite `min < max` |
| `absolute_temperature_range_c` | object | General outer range with finite `min < max` |
| `temperature_notes` | string[] | Crop-stage temperature notes |
| `annual_precipitation_range_mm` | object | Annual range with finite `min < max` |
| `rotation` | object | Return interval, continuous-cropping, disease, and example-rotation rules |
| `sources` | object[] | Source title, URL, and supported fields |

The root of `backend/data/crops.json` is a JSON list. Unsupported numeric values are not guessed. A missing source-supported value is represented by `null` where the schema permits it, and the limitation must be explained.

Supported crop identifiers are:

- `wheat`
- `barley`
- `corn`
- `chickpea`
- `sunflower`
- `canola`
- `potato`
- `processing_tomato`
- `lentil`

`fallow` is not a crop and is not stored as an entry in `crops.json`. It is a special field state accepted only as `previous_crop`.

## 6. Analysis Request

### Request

```http
POST /api/analyze
Content-Type: application/json
```

### Normal user-flow example

```json
{
  "latitude": 40.195,
  "longitude": 29.06,
  "previous_crop": "wheat",
  "current_crop": "chickpea",
  "next_crop": "sunflower",
  "soil_type": "loamy",
  "priority": "water_saving",
  "harvest_start_date": "2027-08-15",
  "harvest_end_date": "2027-09-15"
}
```

### Request fields

| Field | Type | Required | Contract |
|---|---|---:|---|
| `latitude` | number | yes | Between `-90` and `90` |
| `longitude` | number | yes | Between `-180` and `180` |
| `start_date` | date string | conditional | Optional climate-reference start; must be sent together with `end_date` |
| `end_date` | date string | conditional | Optional climate-reference end; must be sent together with `start_date` |
| `previous_crop` | string | yes | Valid crop identifier or `fallow` |
| `current_crop` | string | yes | Valid crop identifier; cannot be `fallow` |
| `next_crop` | string | yes | Valid crop identifier; cannot be `fallow` |
| `soil_type` | string | yes | `sandy`, `loamy`, `clay`, or `silty` |
| `priority` | string | yes | `balanced`, `water_saving`, or `yield` |
| `harvest_start_date` | date string | yes | Planned harvest-window start |
| `harvest_end_date` | date string | yes | Planned harvest-window end |

### Date rules

- `start_date` and `end_date` must be provided together or both omitted.
- The climate-reference start cannot be after the climate-reference end.
- The inclusive climate-reference range may contain at most 1,827 days.
- When both climate-reference dates are omitted, the backend selects the latest five complete calendar years.
- In 2026, the automatic period resolves to `2021-01-01` through `2025-12-31`.
- The automatic period is rolling; the dates are examples of the 2026 result, not a permanently hard-coded contract.
- Harvest start cannot be after harvest end.
- The inclusive harvest window may contain at most 120 days.

`start_date` and `end_date` describe the historical climate-reference period. They do not mean that one crop is grown continuously for five years.

`previous_crop -> current_crop -> next_crop` represents three consecutive planting decisions, not exact multi-year crop durations.

`harvest_start_date` and `harvest_end_date` represent the farmer's intended harvest window. The harvest analysis compares the same month-day window across the available historical seasons. It does not request future NASA observations and is not a weather forecast.

### Bursa snapshot and request order

For the Bursa reference coordinate and the 2021-2025 automatic period, the repository includes a verified 1,826-day historical NASA POWER snapshot. This avoids a repeated NASA request whenever only the crop, soil, priority, or harvest window changes.

The data-source order is:

1. valid fresh cache;
2. bundled Bursa snapshot for the exact supported reference period;
3. live NASA POWER request with bounded retry and concurrency control;
4. valid stale cache if the live request fails;
5. verified Bursa fallback when explicitly allowed and compatible.

## 7. Analysis Response

### Top-level shape

```json
{
  "location": {
    "latitude": 40.195,
    "longitude": 29.06,
    "label": "Bursa, Türkiye"
  },
  "source": {
    "name": "NASA POWER",
    "mode": "demo",
    "time_standard": "LST",
    "requested_start_date": "2021-01-01",
    "requested_end_date": "2025-12-31",
    "start_date": "2021-01-01",
    "end_date": "2025-12-31",
    "last_complete_year": 2025,
    "is_latest_complete_period": true,
    "fallback_used": false,
    "warnings": [
      "Bursa 2021-2025 historical records bundled with the project were used."
    ]
  },
  "summary": {
    "average_temperature_c": 14.1,
    "minimum_temperature_c": -16.2,
    "maximum_temperature_c": 41.1,
    "total_precipitation_mm": 3099.6,
    "dry_days": 1347,
    "longest_dry_spell_days": 69,
    "hot_days": 71,
    "data_completeness_percent": 100.0
  },
  "risk": {
    "level": "high",
    "score": 75,
    "reasons": [
      "A high share of valid precipitation days were classified as dry."
    ]
  },
  "monthly_climate": [
    {
      "month": "2021-01",
      "average_temperature_c": 4.3,
      "precipitation_mm": 205.8
    }
  ],
  "harvest_period_climate": {
    "planned_start_date": "2027-08-15",
    "planned_end_date": "2027-09-15",
    "period_days": 32,
    "seasons_analyzed": 5,
    "historical_windows": [
      {
        "start_date": "2021-08-15",
        "end_date": "2021-09-15"
      }
    ],
    "average_temperature_c": 23.4,
    "average_maximum_temperature_c": 30.7,
    "average_precipitation_mm_per_period": 28.6,
    "average_rainy_days_per_period": 4.2,
    "average_hot_days_per_period": 3.4,
    "data_completeness_percent": 100.0
  },
  "planned_rotation_assessment": {
    "crop_id": "chickpea",
    "crop_name": "Nohut",
    "rotation": ["wheat", "chickpea", "sunflower"],
    "scores": {
      "total": 76,
      "climate": 80,
      "water": 72,
      "soil": 78,
      "rotation": 73
    },
    "advantages": [],
    "risks": [],
    "limitations": []
  },
  "recommendations": [
    {
      "rank": 1,
      "crop_id": "barley",
      "crop_name": "Arpa",
      "rotation": ["wheat", "barley", "sunflower"],
      "scores": {
        "total": 84,
        "climate": 82,
        "water": 91,
        "soil": 78,
        "rotation": 86
      },
      "advantages": [],
      "risks": []
    }
  ]
}
```

User-facing crop names, reasons, warnings, advantages, risks, and limitations may be localized. Stable programmatic fields and identifiers remain language-independent.

### Source fields

| Field | Contract |
|---|---|
| `mode` | `live`, `cache`, or `demo` |
| `requested_start_date`, `requested_end_date` | Requested or automatically resolved reference period |
| `start_date`, `end_date` | Period actually represented by the returned daily records |
| `last_complete_year` | Last complete calendar year at request time |
| `is_latest_complete_period` | Whether the actual period is the latest automatic five-year period |
| `fallback_used` | Whether the requested data required a fallback period/source |
| `warnings` | Human-readable source and fallback notes |

### Source modes

| Mode | Meaning |
|---|---|
| `live` | Newly retrieved from the NASA POWER API |
| `cache` | Previously retrieved valid records reused from cache |
| `demo` | Bundled Bursa historical NASA POWER snapshot or controlled Bursa fallback |

A `demo` mode with `fallback_used: false` means the supported bundled Bursa snapshot was intentionally reused. It does not indicate a failed request. A true fallback must be disclosed through `fallback_used` and `warnings`.

### Monthly climate

Each represented month remains in `monthly_climate`.

- `average_temperature_c` and `precipitation_mm` are `number | null`.
- If a month has no valid measurement for one metric, that metric is `null`.
- If all valid measurements are real zeros, the result is `0.0`.
- A month is not removed merely to hide a data gap.

### Harvest-period climate

`harvest_period_climate` summarizes the same planned calendar window across complete historical seasons. Each average may be `null` only when no valid measurement exists for that metric. `data_completeness_percent` remains visible.

### Crop assessment and alternatives

- `planned_rotation_assessment` always evaluates the selected `current_crop`.
- `recommendations` contains alternatives for the same planned planting, not crops for the season after `current_crop`.
- The selected `current_crop` never appears in `recommendations`.
- At most three alternatives are returned.
- An alternative must have a total score of at least `50`.
- Alternatives are sorted by descending total score and then ascending `crop_id`.
- `rank` starts at `1` and remains consecutive.
- If no suitable alternative exists, `recommendations` is an empty list.
- Repeated crops are not rejected at request validation; the repetition is evaluated as a rotation risk.
- Rules that cannot be proven from only three consecutive crop selections are disclosed through `limitations`.

## 8. Normalized Daily Climate Record

NASA POWER data is normalized before climate analysis:

```json
{
  "date": "2021-01-01",
  "temperature_c": 7.4,
  "temperature_min_c": 1.2,
  "temperature_max_c": 13.8,
  "precipitation_mm": 0.0,
  "relative_humidity_percent": 68.4,
  "root_zone_wetness": 0.57
}
```

| Field | Type and range |
|---|---|
| `date` | ISO date |
| `temperature_c` | finite number or `null` |
| `temperature_min_c` | finite number or `null` |
| `temperature_max_c` | finite number or `null` |
| `precipitation_mm` | finite number or `null` |
| `relative_humidity_percent` | finite number from `0` to `100`, or `null` |
| `root_zone_wetness` | finite number from `0` to `1`, or `null` |

Rules:

- One record represents one date.
- Missing dates and duplicate dates are validated.
- NASA fill values such as `-999` are converted to `null`, never analyzed as observations.
- `RH2M` and `GWETROOT` are enrichment fields. Their partial absence does not stop the core analysis.
- `T2M`, `T2M_MIN`, `T2M_MAX`, and `PRECTOTCORR` are core fields.
- If any one core field is missing for the entire analysis period, climate analysis raises `InsufficientClimateDataError`.
- Real zero values are retained.
- `backend/data/demo_climate.json` follows the same normalized-record contract.

## 9. NASA POWER Request

Endpoint:

```text
https://power.larc.nasa.gov/api/temporal/daily/point
```

Parameters:

```text
community=AG
parameters=T2M,T2M_MIN,T2M_MAX,PRECTOTCORR,RH2M,GWETROOT
format=JSON
time-standard=LST
```

| Parameter | Meaning |
|---|---|
| `T2M` | Mean temperature at two metres |
| `T2M_MIN` | Daily minimum temperature |
| `T2M_MAX` | Daily maximum temperature |
| `PRECTOTCORR` | Corrected daily total precipitation |
| `RH2M` | Relative humidity at two metres |
| `GWETROOT` | Root-zone soil wetness |

Only the backend calls NASA POWER. The browser never calls NASA POWER directly.

The resilience policy uses:

- a 30-second request timeout;
- at most three attempts for retryable failures;
- bounded exponential backoff and jitter;
- bounded `Retry-After` handling;
- a 35-second total retry budget;
- at most four concurrent NASA requests;
- in-flight de-duplication for equivalent requests;
- a seven-day fresh-cache lifetime.

## 10. Prototype Climate Rules

- A day with precipitation below `1 mm` is classified as dry.
- A day with maximum temperature greater than or equal to `35 °C` is classified as hot.
- Risk score `0-33` maps to `low`.
- Risk score `34-66` maps to `medium`.
- Risk score `67-100` maps to `high`.

These are transparent prototype thresholds, not universal agronomic laws.

## 11. Internal Recommendation Contract

The backend creates an enriched copy of the climate-analysis result without mutating the original:

```json
{
  "metadata": {
    "start_date": "2021-01-01",
    "end_date": "2025-12-31",
    "period_days": 1826
  }
}
```

`period_days` must be a positive integer equal to `(end_date - start_date).days + 1`.

Total precipitation is annualized before comparison with crop annual-precipitation ranges:

```text
analysis_years = period_days / 365.2425
annual_precipitation_mm = total_precipitation_mm / analysis_years
```

The recommendation entry point is:

```python
def recommend_rotations(
    *,
    previous_crop: str | None,
    current_crop: str,
    next_crop: str | None,
    soil_type: str,
    priority: str,
    climate_result: dict,
) -> dict:
    ...
```

The internal function supports optional previous/next values, while the public `AnalyzeRequest` currently requires all three crop selections. The function does not mutate `climate_result` and returns a new dictionary containing `planned_rotation_assessment` and `recommendations`.

The module's exception hierarchy is:

```text
RecommendationError
|-- InvalidRecommendationInputError
|   `-- InvalidCropSelectionError
|-- InvalidClimateResultError
`-- CropDataError
```

## 12. Error Responses

Controlled application errors use:

```json
{
  "detail": {
    "code": "NASA_API_UNAVAILABLE",
    "message": "NASA POWER data is currently unavailable."
  }
}
```

| HTTP status | Application code | Meaning |
|---:|---|---|
| `422` | FastAPI validation detail | Invalid field type, missing field, extra field, range, or date relationship |
| `422` | `NASA_VALIDATION_ERROR` | Invalid NASA request parameters |
| `422` | `INSUFFICIENT_CLIMATE_DATA` | A core climate field is absent for the complete period |
| `422` | `INVALID_CROP_SELECTION` | Unknown crop or invalid `fallow` use |
| `422` | `INVALID_RECOMMENDATION_INPUT` | Invalid recommendation input |
| `502` | `NASA_*` service code | NASA timeout, connection, rate-limit, response, or availability failure with no valid fallback |
| `500` | `CLIMATE_ANALYSIS_ERROR` | Normalized climate records violate the analysis contract |
| `500` | `HARVEST_ANALYSIS_ERROR` | Historical harvest-window analysis cannot be produced |
| `500` | `INVALID_CLIMATE_RESULT` | Climate result supplied to recommendation is invalid |
| `500` | `CROP_DATA_ERROR` | Crop data cannot be read or validated |
| `500` | `RECOMMENDATION_ERROR` | Unexpected recommendation-module failure |

The frontend must show a concise user-facing message and must not expose a Python traceback or raw internal exception.

## 13. Module Responsibilities

### Frontend

- Collects location and agricultural planning inputs.
- Calls `GET /api/crops` and `POST /api/analyze`.
- Displays source information, warnings, climate evidence, harvest-window conditions, crop assessment, and alternatives.
- Never calls NASA POWER directly.

### NASA data layer

- Builds and sends NASA POWER requests.
- Normalizes NASA records.
- Converts missing/fill values safely.
- Applies retry, concurrency, cache, bundled-snapshot, and fallback policies.

### Climate analysis

- Validates normalized daily records.
- Produces climate summary, dry/hot indicators, risk score, reasons, and monthly series.
- Performs no network request.

### Harvest-window analysis

- Maps the planned inclusive window to the same month-day span in each complete historical season.
- Produces transparent temperature, precipitation, rainy-day, hot-day, and completeness statistics.
- Performs no future-weather forecast.

### Crop recommendation

- Reads validated crop, water, soil, rotation, and source fields from `crops.json`.
- Evaluates the selected crop plan.
- Produces at most three ranked and explainable alternatives.
- Does not mutate the climate-analysis result or reprocess raw NASA data.

### FastAPI orchestration

- Validates the public request.
- Runs the climate pipeline.
- Adds internal date metadata for recommendation.
- Calls climate, harvest-window, and recommendation modules.
- Validates and returns one combined response.

## 14. Contract Changes

A shared field or structure must not be changed unilaterally.

For every contract change:

1. assess frontend, backend, data, and test impact;
2. update this document;
3. update all affected models and modules;
4. add or update automated tests;
5. describe the change in the pull request.

The final contract is enforced by Pydantic response models and the automated test suite.
