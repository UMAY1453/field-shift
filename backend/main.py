"""Field Shift FastAPI uygulamasının giriş noktası."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.models import HealthResponse


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


@app.get("/api/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Frontend ve geliştiriciler için servis sağlık kontrolü."""

    return HealthResponse()
