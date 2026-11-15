"""Field Shift API veri modelleri.

Bu modül, CONTRACTS.md içinde tanımlanan JSON sözleşmelerini Pydantic
modelleriyle doğrular. NASA verisini analiz eden veya ürün önerisi üreten iş
mantığı burada yer almaz.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SoilType = Literal["sandy", "loamy", "clay", "silty"]
Priority = Literal["balanced", "water_saving", "yield"]
SourceMode = Literal["live", "cache", "demo"]
RiskLevel = Literal["low", "medium", "high"]
GrowingSeason = Literal["spring", "summer", "autumn", "winter"]
WaterNeed = Literal["low", "medium", "high"]
MAX_ANALYSIS_DAYS = 1826


class ApiModel(BaseModel):
    """Bütün API modelleri için ortak ve sıkı doğrulama ayarları."""

    model_config = ConfigDict(
        extra="forbid",
        str_strip_whitespace=True,
        allow_inf_nan=False,
    )


class HealthResponse(ApiModel):
    status: Literal["ok"] = "ok"
    service: Literal["field-shift-api"] = "field-shift-api"


class NumericRange(ApiModel):
    min: float
    max: float

    @model_validator(mode="after")
    def validate_order(self) -> "NumericRange":
        if self.min >= self.max:
            raise ValueError("Aralık minimumu maksimumdan küçük olmalıdır.")
        return self


class CropRotation(ApiModel):
    minimum_return_years: int | None = Field(ge=1)
    avoid_continuous_cropping: bool
    example_rotations: list[list[str]]
    disease_groups: list[str]
    notes: list[str]


class CropSource(ApiModel):
    title: str = Field(min_length=1)
    url: str = Field(min_length=1)
    supports: list[str] = Field(min_length=1)


class Crop(ApiModel):
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    family: str = Field(min_length=1)
    is_legume: bool
    growing_season: list[GrowingSeason] = Field(min_length=1)
    water_need: WaterNeed
    suitable_soils: list[SoilType] = Field(min_length=1)
    soil_notes: list[str]
    temperature_range_c: NumericRange
    absolute_temperature_range_c: NumericRange
    temperature_notes: list[str]
    annual_precipitation_range_mm: NumericRange
    rotation: CropRotation
    sources: list[CropSource] = Field(min_length=1)


class CropsResponse(ApiModel):
    crops: list[Crop]


class AnalyzeRequest(ApiModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    start_date: date
    end_date: date
    previous_crop: str | None = Field(min_length=1)
    current_crop: str = Field(min_length=1)
    next_crop: str | None = Field(min_length=1)
    soil_type: SoilType
    priority: Priority

    @model_validator(mode="after")
    def validate_request_rules(self) -> "AnalyzeRequest":
        if self.start_date > self.end_date:
            raise ValueError(
                "Başlangıç tarihi, bitiş tarihinden sonra olamaz."
            )
        period_days = (self.end_date - self.start_date).days + 1
        if period_days > MAX_ANALYSIS_DAYS:
            raise ValueError("Analiz dönemi en fazla 5 yıl olabilir.")
        if self.current_crop == "fallow" or self.next_crop == "fallow":
            raise ValueError(
                "fallow yalnızca previous_crop alanında kullanılabilir."
            )
        return self


class DailyClimateRecord(ApiModel):
    date: date
    temperature_c: float | None = None
    temperature_min_c: float | None = None
    temperature_max_c: float | None = None
    precipitation_mm: float | None = None
    relative_humidity_percent: float | None = Field(
        default=None,
        ge=0,
        le=100,
    )
    root_zone_wetness: float | None = Field(
        default=None,
        ge=0,
        le=1,
    )


class Location(ApiModel):
    latitude: float
    longitude: float
    label: str


class Source(ApiModel):
    name: str = "NASA POWER"
    mode: SourceMode
    time_standard: Literal["LST"] = "LST"
    start_date: date
    end_date: date


class ClimateSummary(ApiModel):
    average_temperature_c: float
    minimum_temperature_c: float
    maximum_temperature_c: float
    total_precipitation_mm: float
    dry_days: int = Field(ge=0)
    longest_dry_spell_days: int = Field(ge=0)
    hot_days: int = Field(ge=0)
    data_completeness_percent: float = Field(ge=0, le=100)


class ClimateRisk(ApiModel):
    level: RiskLevel
    score: int = Field(ge=0, le=100)
    reasons: list[str]


class MonthlyClimate(ApiModel):
    month: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")
    average_temperature_c: float | None
    precipitation_mm: float | None


class ClimateAnalysisResult(ApiModel):
    summary: ClimateSummary
    risk: ClimateRisk
    monthly_climate: list[MonthlyClimate]


class RecommendationScores(ApiModel):
    total: int = Field(ge=0, le=100)
    climate: int = Field(ge=0, le=100)
    water: int = Field(ge=0, le=100)
    soil: int = Field(ge=0, le=100)
    rotation: int = Field(ge=0, le=100)


class PlannedRotationAssessment(ApiModel):
    crop_id: str = Field(min_length=1)
    crop_name: str = Field(min_length=1)
    rotation: list[str] = Field(min_length=1)
    scores: RecommendationScores
    advantages: list[str]
    risks: list[str]
    limitations: list[str]


class Recommendation(ApiModel):
    rank: int = Field(ge=1, le=3)
    crop_id: str = Field(min_length=1)
    crop_name: str = Field(min_length=1)
    rotation: list[str] = Field(min_length=1)
    scores: RecommendationScores
    advantages: list[str]
    risks: list[str]


class AnalyzeResponse(ApiModel):
    location: Location
    source: Source
    summary: ClimateSummary
    risk: ClimateRisk
    monthly_climate: list[MonthlyClimate]
    planned_rotation_assessment: PlannedRotationAssessment
    recommendations: list[Recommendation] = Field(max_length=3)


class ErrorDetail(ApiModel):
    code: str
    message: str


class ErrorResponse(ApiModel):
    detail: ErrorDetail
