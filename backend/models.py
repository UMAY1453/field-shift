"""Field Shift API veri modelleri.

Bu modül, CONTRACTS.md içinde tanımlanan JSON sözleşmelerini Pydantic
modelleriyle doğrular. NASA verisini analiz eden veya ürün önerisi üreten iş
mantığı burada yer almaz.
"""

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.reference_period import (
    default_reference_end_date,
    default_reference_start_date,
    get_latest_complete_reference_period,
)


SoilType = Literal["sandy", "loamy", "clay", "silty"]
Priority = Literal["balanced", "water_saving", "yield"]
SourceMode = Literal["live", "cache", "demo"]
RiskLevel = Literal["low", "medium", "high"]
GrowingSeason = Literal["spring", "summer", "autumn", "winter"]
WaterNeed = Literal["low", "medium", "high"]
MAX_ANALYSIS_DAYS = 1827
MAX_HARVEST_PERIOD_DAYS = 120
_DEFAULT_REFERENCE_PERIOD = get_latest_complete_reference_period()
DEFAULT_REFERENCE_START_DATE = _DEFAULT_REFERENCE_PERIOD.start_date
DEFAULT_REFERENCE_END_DATE = _DEFAULT_REFERENCE_PERIOD.end_date


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
    start_date: date = Field(default_factory=default_reference_start_date)
    end_date: date = Field(default_factory=default_reference_end_date)
    previous_crop: str = Field(min_length=1)
    current_crop: str = Field(min_length=1)
    next_crop: str = Field(min_length=1)
    soil_type: SoilType
    priority: Priority
    harvest_start_date: date
    harvest_end_date: date

    @model_validator(mode="before")
    @classmethod
    def require_complete_reference_date_pair(cls, values: object) -> object:
        if isinstance(values, dict):
            has_start = "start_date" in values
            has_end = "end_date" in values
            if has_start != has_end:
                raise ValueError(
                    "start_date ve end_date birlikte gönderilmelidir."
                )
        return values

    @model_validator(mode="after")
    def validate_request_rules(self) -> "AnalyzeRequest":
        if self.start_date > self.end_date:
            raise ValueError(
                "Başlangıç tarihi, bitiş tarihinden sonra olamaz."
            )
        period_days = (self.end_date - self.start_date).days + 1
        if period_days > MAX_ANALYSIS_DAYS:
            raise ValueError("Analiz dönemi en fazla 5 yıl olabilir.")
        if self.harvest_start_date > self.harvest_end_date:
            raise ValueError(
                "Hasat başlangıç tarihi, bitiş tarihinden sonra olamaz."
            )
        harvest_period_days = (
            self.harvest_end_date - self.harvest_start_date
        ).days + 1
        if harvest_period_days > MAX_HARVEST_PERIOD_DAYS:
            raise ValueError(
                "Planlanan hasat dönemi en fazla 120 gün olabilir."
            )
        if self.current_crop == "fallow" or self.next_crop == "fallow":
            raise ValueError(
                "fallow yalnızca previous_crop alanında kullanılabilir."
            )
        return self

    @property
    def uses_automatic_reference_period(self) -> bool:
        return not ({"start_date", "end_date"} & self.model_fields_set)


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
    requested_start_date: date
    requested_end_date: date
    start_date: date
    end_date: date
    last_complete_year: int
    is_latest_complete_period: bool
    fallback_used: bool
    warnings: list[str]


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


class HistoricalHarvestWindow(ApiModel):
    start_date: date
    end_date: date


class HarvestPeriodClimate(ApiModel):
    planned_start_date: date
    planned_end_date: date
    period_days: int = Field(ge=1, le=MAX_HARVEST_PERIOD_DAYS)
    seasons_analyzed: int = Field(ge=1)
    historical_windows: list[HistoricalHarvestWindow] = Field(min_length=1)
    average_temperature_c: float | None
    average_maximum_temperature_c: float | None
    average_precipitation_mm_per_period: float | None
    average_rainy_days_per_period: float | None
    average_hot_days_per_period: float | None
    data_completeness_percent: float = Field(ge=0, le=100)


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
    harvest_period_climate: HarvestPeriodClimate
    planned_rotation_assessment: PlannedRotationAssessment
    recommendations: list[Recommendation] = Field(max_length=3)


class ErrorDetail(ApiModel):
    code: str
    message: str


class ErrorResponse(ApiModel):
    detail: ErrorDetail
