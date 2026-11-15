"""Field Shift FastAPI uygulamasının giriş noktası."""

import asyncio

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from backend.climate_analysis import (
    ClimateAnalysisError,
    InsufficientClimateDataError,
)
from backend.climate_pipeline import run_climate_pipeline
from backend.models import (
    AnalyzeRequest,
    AnalyzeResponse,
    CropsResponse,
    ErrorDetail,
    ErrorResponse,
    HealthResponse,
)
from backend.nasa_service import (
    BURSA_DEMO_COORDINATE_TOLERANCE,
    BURSA_DEMO_LATITUDE,
    BURSA_DEMO_LONGITUDE,
    NasaServiceError,
)
from backend.recommendation import (
    CropDataError,
    InvalidClimateResultError,
    InvalidCropSelectionError,
    InvalidRecommendationInputError,
    RecommendationError,
    load_crops,
    recommend_rotations,
)


app = FastAPI(
    title="Field Shift API",
    version="0.1.0",
    description="NASA POWER tabanlı iklim ve ürün rotasyonu karar desteği.",
)

# Frontend geliştirme sırasında ayrı bir yerel sunucuda (5500) çalışıyor.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Accept", "Content-Type"],
)


def _error_response(
    *,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    payload = ErrorResponse(
        detail=ErrorDetail(code=code, message=message),
    )
    return JSONResponse(
        status_code=status_code,
        content=payload.model_dump(mode="json"),
    )


@app.exception_handler(InsufficientClimateDataError)
async def handle_insufficient_climate_data(
    _request: Request,
    error: InsufficientClimateDataError,
) -> JSONResponse:
    """Yetersiz çekirdek iklim verisini kontrollü API hatasına çevirir."""

    return _error_response(
        status_code=422,
        code="INSUFFICIENT_CLIMATE_DATA",
        message=str(error),
    )


@app.exception_handler(ClimateAnalysisError)
async def handle_climate_analysis_error(
    _request: Request,
    error: ClimateAnalysisError,
) -> JSONResponse:
    """Geçersiz dahili iklim kaydını kontrollü API hatasına çevirir."""

    return _error_response(
        status_code=500,
        code="CLIMATE_ANALYSIS_ERROR",
        message=str(error),
    )


@app.exception_handler(NasaServiceError)
async def handle_nasa_service_error(
    _request: Request,
    error: NasaServiceError,
) -> JSONResponse:
    """NASA katmanı hatalarını istemciye kontrollü biçimde aktarır."""

    status_code = 422 if error.code == "NASA_VALIDATION_ERROR" else 502
    return _error_response(
        status_code=status_code,
        code=error.code,
        message=error.message,
    )


@app.exception_handler(InvalidCropSelectionError)
async def handle_invalid_crop_selection(
    _request: Request,
    error: InvalidCropSelectionError,
) -> JSONResponse:
    return _error_response(
        status_code=422,
        code="INVALID_CROP_SELECTION",
        message=str(error),
    )


@app.exception_handler(InvalidRecommendationInputError)
async def handle_invalid_recommendation_input(
    _request: Request,
    error: InvalidRecommendationInputError,
) -> JSONResponse:
    return _error_response(
        status_code=422,
        code="INVALID_RECOMMENDATION_INPUT",
        message=str(error),
    )


@app.exception_handler(InvalidClimateResultError)
async def handle_invalid_climate_result(
    _request: Request,
    error: InvalidClimateResultError,
) -> JSONResponse:
    return _error_response(
        status_code=500,
        code="INVALID_CLIMATE_RESULT",
        message=str(error),
    )


@app.exception_handler(CropDataError)
async def handle_crop_data_error(
    _request: Request,
    error: CropDataError,
) -> JSONResponse:
    return _error_response(
        status_code=500,
        code="CROP_DATA_ERROR",
        message=str(error),
    )


@app.exception_handler(RecommendationError)
async def handle_recommendation_error(
    _request: Request,
    error: RecommendationError,
) -> JSONResponse:
    return _error_response(
        status_code=500,
        code="RECOMMENDATION_ERROR",
        message=str(error),
    )


def _location_label(latitude: float, longitude: float) -> str:
    if (
        abs(latitude - BURSA_DEMO_LATITUDE)
        <= BURSA_DEMO_COORDINATE_TOLERANCE
        and abs(longitude - BURSA_DEMO_LONGITUDE)
        <= BURSA_DEMO_COORDINATE_TOLERANCE
    ):
        return "Bursa, Türkiye"
    return f"{latitude:.4f}, {longitude:.4f}"


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Frontend ve geliştiriciler için servis sağlık kontrolü."""

    return HealthResponse()


@app.get("/api/crops", response_model=CropsResponse)
async def list_crops() -> CropsResponse:
    """Frontend seçimleri için doğrulanmış ürün listesini döndürür."""

    crops_by_id = await asyncio.to_thread(load_crops)
    return CropsResponse(crops=list(crops_by_id.values()))


@app.post("/api/analyze", response_model=AnalyzeResponse)
async def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    """NASA, iklim analizi ve rotasyon önerisini tek cevapta birleştirir."""

    pipeline_result = await run_climate_pipeline(
        latitude=request.latitude,
        longitude=request.longitude,
        start_date=request.start_date,
        end_date=request.end_date,
    )
    climate_result = pipeline_result.analysis.model_dump(mode="json")
    period_days = (request.end_date - request.start_date).days + 1
    enriched_climate_result = {
        **climate_result,
        "metadata": {
            "start_date": request.start_date.isoformat(),
            "end_date": request.end_date.isoformat(),
            "period_days": period_days,
        },
    }

    rotation_result = await asyncio.to_thread(
        recommend_rotations,
        previous_crop=request.previous_crop,
        current_crop=request.current_crop,
        next_crop=request.next_crop,
        soil_type=request.soil_type,
        priority=request.priority,
        climate_result=enriched_climate_result,
    )

    payload = {
        "location": {
            "latitude": request.latitude,
            "longitude": request.longitude,
            "label": _location_label(request.latitude, request.longitude),
        },
        "source": {
            "name": "NASA POWER",
            "mode": pipeline_result.source.mode,
            "time_standard": "LST",
            "start_date": request.start_date,
            "end_date": request.end_date,
        },
        **climate_result,
        **rotation_result,
    }
    try:
        return AnalyzeResponse.model_validate(payload)
    except ValidationError as exc:
        raise RecommendationError(
            "Birleşik analiz sonucu API cevap sözleşmesine uymuyor."
        ) from exc
