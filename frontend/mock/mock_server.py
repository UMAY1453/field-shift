import json
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field


# Mock JSON dosyalarının bulunduğu klasör.
MOCK_DIRECTORY = Path(__file__).resolve().parent


class AnalysisRequest(BaseModel):
    """Frontend analiz isteğinin test modelidir."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    start_date: str
    end_date: str
    current_crop: str
    soil_type: str
    priority: str


app = FastAPI(
    title="Field Shift Mock API",
    description="Frontend geliştirmesi için geçici test servisi.",
    version="1.0.0",
)


# Frontend'in 5500 portundan API'ye bağlanmasına izin verir.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


def read_mock_json(file_name: str) -> dict:
    """Belirtilen mock JSON dosyasını okur."""

    file_path = MOCK_DIRECTORY / file_name

    with file_path.open("r", encoding="utf-8") as file:
        return json.load(file)


@app.get("/api/health")
def health() -> dict:
    """Frontend sağlık kontrolüne başarılı cevap verir."""

    return {
        "status": "ok",
        "service": "field-shift-mock-api",
    }


@app.get("/api/crops")
def get_crops() -> dict:
    """Test ürün listesini döndürür."""

    return read_mock_json("crops.json")


@app.post("/api/analyze")
def analyze(request: AnalysisRequest) -> dict:
    """Sözleşmeye uygun sahte analiz cevabı döndürür."""

    result = read_mock_json("analysis.json")

    # Kullanıcının seçtiği koordinatları cevaba aktarır.
    result["location"]["latitude"] = request.latitude
    result["location"]["longitude"] = request.longitude
    result["location"]["label"] = "Seçilen demo konum"

    # Kullanıcının tarih aralığını kaynak bilgisine aktarır.
    result["source"]["start_date"] = request.start_date
    result["source"]["end_date"] = request.end_date

    return result


if __name__ == "__main__":
    # Mock API gerçek backend ile aynı portta çalışır.
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8000,
    )