"""Field Shift FastAPI uygulamasının giriş noktası."""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.climate_analysis import (
    ClimateAnalysisError,
    InsufficientClimateDataError,
)
from backend.models import ErrorDetail, ErrorResponse, HealthResponse


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


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Frontend ve geliştiriciler için servis sağlık kontrolü."""

    return HealthResponse()
