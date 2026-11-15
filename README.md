# Field Shift

**Turning NASA POWER climate data into explainable crop and harvest-planning decisions.**

[Live Application](https://field-shift-mocha-sigma.vercel.app) | [API Health Check](https://field-shift-mocha-sigma.vercel.app/api/health) | [Technical Contracts](CONTRACTS.md) | [Contributing](CONTRIBUTING.md)

Field Shift is an open-source agricultural decision-support prototype developed for a NASA-focused hackathon. It combines recent historical climate evidence, the farmer's crop sequence, soil type, planning priority, and intended harvest window in one workflow.

The system does **not** provide a weather forecast, a yield guarantee, or professional agronomic advice. It turns historical evidence into transparent planning support.

## The Problem

Climate data is available, but raw daily measurements do not directly answer practical questions such as:

- How unusual are the recent heat and dry-spell conditions?
- What conditions have historically occurred during a planned harvest window?
- Does the planned crop fit the available climate, water demand, soil, and crop-rotation context?
- Which alternatives may be more suitable, and why?

Field Shift connects these questions in a single, explainable workflow.

## How It Works

1. The user selects a location in Bursa, Türkiye.
2. The user provides the previous, planned, and following crops; soil type; planning priority; and planned harvest dates.
3. The backend automatically selects the latest five complete calendar years as the reference period.
4. Daily climate records are normalized and analyzed for temperature, precipitation, dry spells, hot days, and data completeness.
5. The planned harvest window is compared with the same calendar window across the five historical seasons.
6. The planned crop sequence is assessed using climate, water demand, soil suitability, and rotation compatibility.
7. The application returns the planned-crop assessment and up to three explainable alternatives.

```text
Browser
  |
  | JSON request
  v
FastAPI application
  |
  +-- NASA POWER data service / cache / bundled Bursa snapshot
  +-- Climate analysis
  +-- Historical harvest-window analysis
  +-- Crop-rotation recommendation engine
  |
  v
Validated JSON response
  |
  v
Map, charts, risk explanation, and crop alternatives
```

The frontend never calls NASA POWER directly. External climate requests and all analytical operations are handled by the backend.

## Key Features

- Interactive Leaflet location selection
- Automatically rolling five-complete-year reference period
- Daily NASA POWER temperature, precipitation, humidity, and root-zone wetness signals
- Monthly climate summaries and visible data-completeness reporting
- Explainable 0-100 climate-risk score
- Dry-day, longest-dry-spell, and hot-day indicators
- Historical comparison of the farmer's planned harvest window
- Assessment of the previous -> planned -> following crop sequence
- Up to three ranked crop alternatives with advantages, risks, and limitations
- Responsive interface for desktop and mobile devices
- Retry, concurrency control, request de-duplication, cache, and controlled fallback behavior
- One live URL serving both the frontend and backend

## Climate Data

Field Shift uses the NASA POWER Daily API with:

```text
community=AG
format=JSON
time-standard=LST
```

| NASA parameter | Normalized field | Meaning |
|---|---|---|
| `T2M` | `temperature_c` | Daily mean temperature |
| `T2M_MIN` | `temperature_min_c` | Daily minimum temperature |
| `T2M_MAX` | `temperature_max_c` | Daily maximum temperature |
| `PRECTOTCORR` | `precipitation_mm` | Corrected daily total precipitation |
| `RH2M` | `relative_humidity_percent` | Relative humidity at two metres |
| `GWETROOT` | `root_zone_wetness` | Root-zone soil wetness |

`T2M`, `T2M_MIN`, `T2M_MAX`, and `PRECTOTCORR` are core analysis fields. `RH2M` and `GWETROOT` enrich the dataset; missing values in these two fields are preserved as `null` without stopping the core analysis. A real numeric `0` is retained as valid data and is never treated as missing.

### Reference period

When climate dates are omitted from an analysis request, the backend selects the latest five complete calendar years. In 2026, this resolves to `2021-01-01` through `2025-12-31`. The window can roll forward in later years without changing the API contract.

The current validated pilot scope is Bursa. For the Bursa reference location and 2021-2025 period, the repository includes a verified 1,826-day historical NASA POWER snapshot. Reusing this snapshot makes the public demo deterministic and avoids unnecessary repeated requests to NASA POWER. Other supported requests follow the normal cache and live-request pipeline.

The API reports the source mode transparently:

- `live`: newly retrieved from NASA POWER;
- `cache`: previously retrieved valid data reused from cache;
- `demo`: the bundled Bursa historical snapshot or controlled Bursa fallback was used.

## Harvest-Window Analysis

The required `harvest_start_date` and `harvest_end_date` fields describe the farmer's planned harvest window, not the climate-reference period. The window may contain at most 120 days.

Field Shift compares the same month-day window across each available historical season and reports:

- number of seasons analyzed;
- average and average-maximum temperature;
- average precipitation per period;
- average rainy days per period;
- average hot days per period;
- data completeness.

This is historical evidence for planning. It is **not** a forecast of the weather on the selected future dates.

## Crop Decisions

The recommendation engine evaluates:

- climate compatibility;
- crop water demand;
- selected soil type;
- previous, planned, and following crop compatibility;
- the user's priority: `balanced`, `water_saving`, or `yield`.

The planned crop is always assessed. When suitable alternatives exist, the system returns at most three, excludes the already selected crop, and explains the benefits, risks, and known limitations behind each score.

Supported crop identifiers currently include wheat, barley, corn, chickpea, sunflower, canola, potato, processing tomato, and lentil. `fallow` is a special previous-field state rather than a crop.

## Reliability and Validation

The data layer includes safeguards for common external-API and data-quality failures:

- bounded retries for rate limits, timeouts, connection failures, and temporary NASA service errors;
- respect for bounded `Retry-After` values;
- a maximum of four concurrent NASA requests;
- in-flight request de-duplication;
- cache validation and atomic cache writes;
- rejection of non-finite numbers and NASA fill values such as `-999`;
- preservation of valid zero values;
- explicit `null` handling and data-completeness reporting;
- controlled error responses instead of fabricated zero-filled analysis.

The final repository test suite contains **179 passing automated tests**. The public deployment has also been checked end to end: the frontend, health endpoint, and combined analysis endpoint return successful responses.

## API

| Method | Endpoint | Purpose |
|---|---|---|
| `GET` | `/api/health` | Service health check |
| `GET` | `/api/crops` | Lightweight crop list for the interface |
| `POST` | `/api/analyze` | Combined climate, harvest-window, and crop-rotation analysis |

### Example request

The normal user flow omits climate-reference dates and lets the backend select the latest five complete years:

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

Optional `start_date` and `end_date` values may be supplied together for an explicit climate-reference period of at most 1,827 days. Full request, response, validation, and error contracts are documented in [CONTRACTS.md](CONTRACTS.md).

## Technology Stack

### Frontend

- HTML5
- CSS3
- JavaScript
- Leaflet
- Chart.js

### Backend

- Python 3.12 or newer (developed and tested with Python 3.14.8)
- FastAPI
- Pydantic
- HTTPX
- Uvicorn for local development

### Quality and deployment

- Pytest and Pytest Asyncio
- Vercel
- Apache License 2.0

## Project Structure

```text
field-shift/
|-- backend/
|   |-- data/
|   |   |-- crops.json
|   |   `-- demo_climate.json
|   |-- climate_analysis.py
|   |-- climate_pipeline.py
|   |-- harvest_analysis.py
|   |-- main.py
|   |-- models.py
|   |-- nasa_service.py
|   |-- recommendation.py
|   `-- reference_period.py
|-- frontend/
|   |-- assets/
|   |-- css/
|   |-- js/
|   `-- index.html
|-- tests/
|-- CONTRACTS.md
|-- CONTRIBUTING.md
|-- LICENSE
|-- README.md
|-- pyproject.toml
|-- pytest.ini
|-- requirements.txt
`-- vercel.json
```

## Local Setup

### 1. Clone the repository

```powershell
git clone https://github.com/UMAY1453/field-shift.git
Set-Location field-shift
```

### 2. Create and activate a virtual environment

```powershell
py -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
.\.venv\Scripts\Activate.ps1
```

On macOS or Linux, activate it with:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 4. Run the application

```powershell
python -m uvicorn backend.main:app --reload
```

Open:

- Application: <http://127.0.0.1:8000>
- Interactive API documentation: <http://127.0.0.1:8000/docs>
- Health check: <http://127.0.0.1:8000/api/health>

FastAPI serves both the API routes and the frontend, so a second local frontend server is not required.

## Tests

Run the complete suite:

```powershell
python -m pytest -q
```

Run with detailed test names:

```powershell
python -m pytest -v
```

## Deployment

The production application is available at:

<https://field-shift-mocha-sigma.vercel.app>

The Vercel deployment serves the frontend and FastAPI backend from the same origin. This avoids a production dependency on `localhost` and keeps browser requests under one public URL.

This repository is currently deployed manually rather than through automatic GitHub deployment. After an application-code change, deploy the existing Vercel project from the repository root:

```powershell
npx.cmd vercel@latest --prod
```

On macOS or Linux:

```bash
npx vercel@latest --prod
```

Always link to the existing `field-shift` Vercel project instead of creating a new project. The stable production alias is also the target encoded in the presentation QR code.

Documentation-only changes do not require a new Vercel deployment.

## Data and Agronomic Sources

- [NASA POWER Project](https://power.larc.nasa.gov/) - daily climate data
- [FAO EcoCrop](https://ecocrop.apps.fao.org/ecocrop/srv/en/home) - crop ecological characteristics
- [FAO Crop Water Needs](https://www.fao.org/4/S2022E/s2022e07.htm) - crop water-demand context
- [Republic of Türkiye Ministry of Agriculture and Forestry](https://www.tarimorman.gov.tr/) - crop production and protection guidance
- Ministry-affiliated agricultural research institutes and TAGEM technical publications - crop-specific cultivation and rotation guidance

Crop-specific source URLs and the fields supported by each source are stored alongside the corresponding entries in `backend/data/crops.json`.

## Scope and Limitations

- The current validated pilot scope is Bursa, Türkiye.
- Five recent complete years provide a practical recent-history window, not a complete model of long-term climate change.
- Risk thresholds and recommendation weights are prototype assumptions and remain visible through explainable outputs.
- Local soil measurements, field sensors, pest observations, market conditions, and farm-management history are not yet integrated.
- Recommendations support human decisions and do not replace weather forecasts, field measurements, or agronomic expertise.

## Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before proposing a change. API field names and shared structures must remain consistent with [CONTRACTS.md](CONTRACTS.md).

## License

Field Shift is released under the [Apache License 2.0](LICENSE).

## Climate Data Attribution

Climate data is provided by the NASA Prediction Of Worldwide Energy Resources (POWER) Project.
