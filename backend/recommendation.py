"""Ürün rotasyonu değerlendirme ve öneri yardımcıları."""

import json
import math
from datetime import date
from pathlib import Path


CROPS_PATH = Path(__file__).with_name("data") / "crops.json"
ALLOWED_SOIL_TYPES = {"sandy", "loamy", "clay", "silty"}
ALLOWED_PRIORITIES = {"balanced", "water_saving", "yield"}
MIN_RECOMMENDATION_SCORE = 50

PRIORITY_WEIGHTS = {
    "balanced": {"climate": 0.30, "water": 0.25, "soil": 0.20, "rotation": 0.25},
    "water_saving": {"climate": 0.25, "water": 0.35, "soil": 0.15, "rotation": 0.25},
    "yield": {"climate": 0.35, "water": 0.20, "soil": 0.20, "rotation": 0.25},
}


class RecommendationError(Exception):
    """Rotasyon modülündeki hataların temel sınıfı."""


class InvalidRecommendationInputError(RecommendationError):
    """Kullanıcıdan gelen öneri girdileri sözleşmeye uymadığında oluşur."""


class InvalidCropSelectionError(InvalidRecommendationInputError):
    """İstek geçersiz veya desteklenmeyen bir ürün içerdiğinde oluşur."""


class InvalidClimateResultError(RecommendationError):
    """İklim sonucu yıllık karşılaştırma için yetersiz olduğunda oluşur."""


class CropDataError(RecommendationError):
    """Ürün veri dosyası okunamadığında veya temel yapısı bozuk olduğunda oluşur."""


def load_crops(crops_path: Path = CROPS_PATH) -> dict[str, dict]:
    """Ürün listesini kimlikleriyle indekslenmiş biçimde yükler."""

    try:
        crops = json.loads(crops_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise CropDataError("Ürün veri dosyası okunamadı.") from exc

    if not isinstance(crops, list):
        raise CropDataError("Ürün veri dosyasının kökü bir liste olmalıdır.")

    crops_by_id = {}
    for crop in crops:
        if not isinstance(crop, dict):
            raise CropDataError("Her ürün kaydı bir nesne olmalıdır.")

        crop_id = crop.get("id")
        if not isinstance(crop_id, str) or not crop_id.strip():
            raise CropDataError("Her ürünün geçerli bir kimliği olmalıdır.")
        if crop_id in crops_by_id:
            raise CropDataError(f"Tekrarlanan ürün kimliği: {crop_id}")

        crops_by_id[crop_id] = crop

    return crops_by_id


def validate_crop_selections(
    previous_crop: str | None,
    current_crop: str,
    next_crop: str | None,
    crop_ids: set[str],
) -> None:
    """Önceki, mevcut ve sonraki ürün alanlarının sözleşmeye uyumunu doğrular."""

    if current_crop not in crop_ids:
        raise InvalidCropSelectionError(
            "current_crop, crops.json içindeki geçerli bir ürün olmalıdır."
        )

    if previous_crop is not None and previous_crop != "fallow":
        if previous_crop not in crop_ids:
            raise InvalidCropSelectionError(
                "previous_crop; null, fallow veya geçerli bir ürün olmalıdır."
            )

    if next_crop is not None:
        if next_crop == "fallow" or next_crop not in crop_ids:
            raise InvalidCropSelectionError(
                "next_crop; null veya crops.json içindeki geçerli bir ürün olmalıdır."
            )


def validate_recommendation_inputs(
    *,
    previous_crop: str | None,
    current_crop: str,
    next_crop: str | None,
    soil_type: str,
    priority: str,
    crop_ids: set[str],
) -> None:
    """Ana öneri fonksiyonunun kullanıcı girdilerini birlikte doğrular."""

    validate_crop_selections(
        previous_crop,
        current_crop,
        next_crop,
        crop_ids,
    )

    if soil_type not in ALLOWED_SOIL_TYPES:
        raise InvalidRecommendationInputError(
            "soil_type; sandy, loamy, clay veya silty olmalıdır."
        )

    if priority not in ALLOWED_PRIORITIES:
        raise InvalidRecommendationInputError(
            "priority; balanced, water_saving veya yield olmalıdır."
        )


def _is_finite_number(value: object) -> bool:
    """Boolean olmayan sonlu bir int veya float değerini tanır."""

    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(value)
    )


def _validated_climate_period(climate_result: dict) -> tuple[int, float, float]:
    """İklim dönemi, toplam yağış ve veri tamlığı alanlarını doğrular."""

    try:
        metadata = climate_result["metadata"]
        summary = climate_result["summary"]
        start_date = date.fromisoformat(metadata["start_date"])
        end_date = date.fromisoformat(metadata["end_date"])
        period_days = metadata["period_days"]
        total_precipitation = summary["total_precipitation_mm"]
        data_completeness = summary["data_completeness_percent"]
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidClimateResultError(
            "İklim sonucu geçerli metadata, toplam yağış ve veri tamlığı içermelidir."
        ) from exc

    if end_date < start_date:
        raise InvalidClimateResultError(
            "İklim analizinin end_date değeri start_date değerinden önce olamaz."
        )

    expected_period_days = (end_date - start_date).days + 1
    if (
        isinstance(period_days, bool)
        or not isinstance(period_days, int)
        or period_days <= 0
    ):
        raise InvalidClimateResultError(
            "period_days pozitif bir tam sayı olmalıdır."
        )
    if period_days != expected_period_days:
        raise InvalidClimateResultError(
            "period_days, start_date ve end_date arasındaki dahilî gün sayısıyla "
            "eşleşmelidir."
        )

    if (
        not _is_finite_number(total_precipitation)
        or total_precipitation < 0
    ):
        raise InvalidClimateResultError(
            "total_precipitation_mm sıfır veya daha büyük sonlu bir sayı olmalıdır."
        )

    if (
        not _is_finite_number(data_completeness)
        or not 0 <= data_completeness <= 100
    ):
        raise InvalidClimateResultError(
            "data_completeness_percent 0 ile 100 arasında sonlu bir sayı olmalıdır."
        )

    return period_days, float(total_precipitation), float(data_completeness)


def calculate_annual_precipitation_mm(climate_result: dict) -> float:
    """Analiz dönemi toplam yağışını yıllık ortalama yağışa dönüştürür."""

    period_days, total_precipitation, _ = _validated_climate_period(
        climate_result
    )
    analysis_years = period_days / 365.2425
    return total_precipitation / analysis_years


def build_climate_limitations(climate_result: dict) -> list[str]:
    """Eksik iklim verisinin yıllık değerlendirmeye etkisini açıklar."""

    _, _, data_completeness = _validated_climate_period(climate_result)
    if data_completeness == 100:
        return []

    return [
        f"İklim verisi %{data_completeness:g} oranında tamamlanmıştır; "
        "yıllık yağış değerlendirmesi eksik günlerden etkilenebilir."
    ]


def build_minimum_return_limitations(
    rotation: list[str],
    crops_by_id: dict[str, dict],
) -> list[str]:
    """Kısa ürün zinciriyle doğrulanamayan dönüş süresi kurallarını açıklar."""

    limitations = []
    seen_crop_ids = set()

    for crop_id in rotation:
        if crop_id == "fallow" or crop_id in seen_crop_ids:
            continue
        seen_crop_ids.add(crop_id)

        crop = crops_by_id[crop_id]
        minimum_years = crop["rotation"]["minimum_return_years"]
        if minimum_years is None:
            continue

        limitations.append(
            f"{crop['name']} için önerilen minimum dönüş süresi "
            f"{minimum_years} yıldır; mevcut ürün zinciri bu süreyi kesin "
            "doğrulamak için yeterli değildir."
        )

    return limitations

#Kişi-2'nin ana branchinden gelen verileri değerlendirmede kullanılacak sıralamasını hazırlamak 
#Bu pre veya next kısmı yoksa diye
def build_rotation_path(
    previous_crop: str | None,
    candidate_crop: str,
    next_crop: str | None,
) -> list[str]:
    """Bilinen ürünleri tarımsal sıralarını koruyarak döndürür.

    ``candidate_crop`` kullanıcının seçtiği mevcut aday veya algoritmanın
    değerlendirdiği alternatif üründür. Önceki ürün bilinmiyorsa ve sonraki ürün
    planlanmamışsa bu değerler rotasyon yoluna eklenmez. ``fallow`` bilinmeyen
    geçmişten farklı, bilinen bir arazi durumu olduğu için korunur.
    """

    if not isinstance(candidate_crop, str) or not candidate_crop.strip():
        raise InvalidCropSelectionError(
            "Değerlendirilecek ürün kimliği boş olamaz."
        )

    rotation = []

    if previous_crop is not None:
        rotation.append(previous_crop)

    rotation.append(candidate_crop)

    if next_crop is not None:
        rotation.append(next_crop)

    return rotation


#Bu 3 lüyü pre-candidate   /    candidate - next diye ayırır
def build_rotation_pairs(rotation: list[str]) -> list[tuple[str, str]]:
    """Rotasyon yolundaki birbirini izleyen ürün çiftlerini döndürür."""

    return list(zip(rotation, rotation[1:]))


def _validated_temperature_summary(
    climate_result: dict,
) -> tuple[float, float, float]:
    """Puanlamada kullanılan sıcaklık özetini doğrular."""

    try:
        summary = climate_result["summary"]
        average = summary["average_temperature_c"]
        minimum = summary["minimum_temperature_c"]
        maximum = summary["maximum_temperature_c"]
    except (KeyError, TypeError) as exc:
        raise InvalidClimateResultError(
            "İklim sonucu ortalama, minimum ve maksimum sıcaklığı içermelidir."
        ) from exc

    temperature_values = {
        "average_temperature_c": average,
        "minimum_temperature_c": minimum,
        "maximum_temperature_c": maximum,
    }
    for field_name, value in temperature_values.items():
        if not _is_finite_number(value):
            raise InvalidClimateResultError(
                f"{field_name} boolean olmayan sonlu bir sayı olmalıdır."
            )

    if minimum > maximum:
        raise InvalidClimateResultError(
            "minimum_temperature_c, maximum_temperature_c değerinden büyük olamaz."
        )
    if not minimum <= average <= maximum:
        raise InvalidClimateResultError(
            "average_temperature_c minimum ve maksimum sıcaklık arasında olmalıdır."
        )

    return float(average), float(minimum), float(maximum)


def _score_value_against_range(value: float, minimum: float, maximum: float) -> int:
    """Bir değeri hedef aralığa uzaklığına göre 0–100 arasında puanlar."""

    if minimum <= value <= maximum:
        return 100

    width = maximum - minimum
    distance = minimum - value if value < minimum else value - maximum
    relative_distance = distance / width

    if relative_distance <= 0.10:
        return 80
    if relative_distance <= 0.25:
        return 60
    if relative_distance <= 0.50:
        return 30
    return 0


def _append_unique(items: list[str], message: str) -> None:
    """Aynı açıklamanın sonuçta tekrarlanmasını önler."""

    if message not in items:
        items.append(message)


def _score_climate(
    crop: dict,
    temperature_summary: tuple[float, float, float],
) -> tuple[int, list[str], list[str]]:
    """Ürünün ortalama ve uç sıcaklık uygunluğunu puanlar."""

    average, minimum, maximum = temperature_summary
    optimal = crop["temperature_range_c"]
    absolute = crop["absolute_temperature_range_c"]
    score = _score_value_against_range(
        average,
        optimal["min"],
        optimal["max"],
    )
    advantages: list[str] = []
    risks: list[str] = []

    if optimal["min"] <= average <= optimal["max"]:
        advantages.append("Ortalama sıcaklık ürünün optimum aralığındadır.")
    else:
        risks.append("Ortalama sıcaklık ürünün optimum aralığının dışındadır.")

    if minimum < absolute["min"]:
        score -= 10
        risks.append("Dönemin minimum sıcaklığı ürünün genel ekolojik alt sınırının altındadır.")
    if maximum > absolute["max"]:
        score -= 10
        risks.append("Dönemin maksimum sıcaklığı ürünün genel ekolojik üst sınırının üzerindedir.")

    return max(0, score), advantages, risks


def _score_water(
    crop: dict,
    annual_precipitation_mm: float,
    priority: str,
) -> tuple[int, list[str], list[str]]:
    """Yıllık yağış ve ürünün su sınıfını puanlar."""

    precipitation_range = crop["annual_precipitation_range_mm"]
    score = _score_value_against_range(
        annual_precipitation_mm,
        precipitation_range["min"],
        precipitation_range["max"],
    )
    advantages: list[str] = []
    risks: list[str] = []

    if precipitation_range["min"] <= annual_precipitation_mm <= precipitation_range["max"]:
        advantages.append("Yıllık ortalama yağış ürünün önerilen aralığındadır.")
    elif annual_precipitation_mm < precipitation_range["min"]:
        risks.append("Yıllık ortalama yağış ürünün önerilen alt sınırının altındadır.")
    else:
        risks.append("Yıllık ortalama yağış ürünün önerilen üst sınırının üzerindedir.")

    if priority == "water_saving":
        if crop["water_need"] == "low":
            score += 10
            advantages.append("Düşük su ihtiyacı su tasarrufu önceliğiyle uyumludur.")
        elif crop["water_need"] == "high":
            score -= 15
            risks.append("Yüksek su ihtiyacı su tasarrufu önceliğiyle çelişebilir.")

    return min(100, max(0, score)), advantages, risks


def _score_soil(crop: dict, soil_type: str) -> tuple[int, list[str], list[str]]:
    """Kullanıcının toprak kodunu ürünün uygun topraklarıyla karşılaştırır."""

    if soil_type in crop["suitable_soils"]:
        return 100, ["Seçilen toprak türü ürünle uyumludur."], []

    return 40, [], ["Seçilen toprak türü ürünün önerilen toprakları arasında değildir."]


def _pair_has_documented_example(
    source_crop: str,
    target_crop: str,
    crops_by_id: dict[str, dict],
) -> bool:
    """Ürün çiftinin kaynaklı örnek rotasyonlardan birinde geçip geçmediğini bulur."""

    for crop in crops_by_id.values():
        for example in crop["rotation"]["example_rotations"]:
            if (source_crop, target_crop) in build_rotation_pairs(example):
                return True
    return False


def _score_rotation(
    rotation: list[str],
    crops_by_id: dict[str, dict],
) -> tuple[int, list[str], list[str]]:
    """Ardışık ürün geçişlerini aile, hastalık ve kaynak örnekleriyle puanlar."""

    score = 100
    advantages: list[str] = []
    risks: list[str] = []

    for source_id, target_id in build_rotation_pairs(rotation):
        if source_id == "fallow":
            _append_unique(advantages, "Nadas durumu ürün tekrarından ayrı değerlendirilmiştir.")
            continue

        source = crops_by_id[source_id]
        target = crops_by_id[target_id]

        if source_id == target_id:
            score -= 50
            _append_unique(risks, "Aynı ürünün arka arkaya yetiştirilmesi rotasyon riski oluşturur.")
        elif source["family"] == target["family"]:
            score -= 25
            _append_unique(risks, "Ardışık ürünler aynı botanik ailedendir.")
        else:
            _append_unique(advantages, "Ardışık ürünler farklı botanik ailelerdendir.")

        common_disease_groups = set(source["rotation"]["disease_groups"]) & set(
            target["rotation"]["disease_groups"]
        )
        if common_disease_groups:
            score -= 20
            _append_unique(risks, "Ardışık ürünler ortak hastalık veya konukçu riski taşır.")

        if target["is_legume"] and not source["is_legume"]:
            score += 5
            _append_unique(advantages, "Tahıl veya baklagil olmayan üründen baklagile geçiş çeşitlilik sağlar.")

        if _pair_has_documented_example(source_id, target_id, crops_by_id):
            score += 5
            _append_unique(advantages, "Ürün geçişi kaynaklı rotasyon örneklerinde yer almaktadır.")

    return min(100, max(0, score)), advantages, risks


def _build_candidate_assessment(
    *,
    previous_crop: str | None,
    candidate_crop: str,
    next_crop: str | None,
    soil_type: str,
    priority: str,
    crops_by_id: dict[str, dict],
    temperature_summary: tuple[float, float, float],
    annual_precipitation_mm: float,
    include_limitations: bool,
    climate_result: dict,
) -> dict:
    """Tek bir mevcut/alternatif ürün için sözleşmeye uygun değerlendirme üretir."""

    crop = crops_by_id[candidate_crop]
    rotation = build_rotation_path(previous_crop, candidate_crop, next_crop)
    climate_score, climate_advantages, climate_risks = _score_climate(
        crop,
        temperature_summary,
    )
    water_score, water_advantages, water_risks = _score_water(
        crop,
        annual_precipitation_mm,
        priority,
    )
    soil_score, soil_advantages, soil_risks = _score_soil(crop, soil_type)
    rotation_score, rotation_advantages, rotation_risks = _score_rotation(
        rotation,
        crops_by_id,
    )

    component_scores = {
        "climate": climate_score,
        "water": water_score,
        "soil": soil_score,
        "rotation": rotation_score,
    }
    weights = PRIORITY_WEIGHTS[priority]
    total_score = round(
        sum(component_scores[name] * weights[name] for name in component_scores)
    )

    assessment = {
        "crop_id": candidate_crop,
        "crop_name": crop["name"],
        "rotation": rotation,
        "scores": {"total": total_score, **component_scores},
        "advantages": climate_advantages
        + water_advantages
        + soil_advantages
        + rotation_advantages,
        "risks": climate_risks + water_risks + soil_risks + rotation_risks,
    }

    if include_limitations:
        limitations = build_climate_limitations(climate_result)
        limitations.extend(build_minimum_return_limitations(rotation, crops_by_id))
        if previous_crop is None:
            limitations.append("Önceki ürün bilinmediği için geçmiş rotasyon ilişkisi değerlendirilemedi.")
        if next_crop is None:
            limitations.append("Sonraki ürün planlanmadığı için ileri rotasyon ilişkisi değerlendirilemedi.")
        assessment["limitations"] = limitations

    return assessment


def recommend_rotations(
    *,
    previous_crop: str | None,
    current_crop: str,
    next_crop: str | None,
    soil_type: str,
    priority: str,
    climate_result: dict,
) -> dict:
    """Seçilen planı değerlendirir ve en fazla üç açıklanabilir alternatif üretir."""

    crops_by_id = load_crops()
    validate_recommendation_inputs(
        previous_crop=previous_crop,
        current_crop=current_crop,
        next_crop=next_crop,
        soil_type=soil_type,
        priority=priority,
        crop_ids=set(crops_by_id),
    )
    temperature_summary = _validated_temperature_summary(climate_result)
    annual_precipitation_mm = calculate_annual_precipitation_mm(climate_result)

    planned_assessment = _build_candidate_assessment(
        previous_crop=previous_crop,
        candidate_crop=current_crop,
        next_crop=next_crop,
        soil_type=soil_type,
        priority=priority,
        crops_by_id=crops_by_id,
        temperature_summary=temperature_summary,
        annual_precipitation_mm=annual_precipitation_mm,
        include_limitations=True,
        climate_result=climate_result,
    )

    candidates = []
    for candidate_crop in crops_by_id:
        if candidate_crop == current_crop:
            continue
        assessment = _build_candidate_assessment(
            previous_crop=previous_crop,
            candidate_crop=candidate_crop,
            next_crop=next_crop,
            soil_type=soil_type,
            priority=priority,
            crops_by_id=crops_by_id,
            temperature_summary=temperature_summary,
            annual_precipitation_mm=annual_precipitation_mm,
            include_limitations=False,
            climate_result=climate_result,
        )
        if assessment["scores"]["total"] >= MIN_RECOMMENDATION_SCORE:
            candidates.append(assessment)

    candidates.sort(key=lambda item: (-item["scores"]["total"], item["crop_id"]))
    recommendations = []
    for rank, assessment in enumerate(candidates[:3], start=1):
        recommendations.append({"rank": rank, **assessment})

    return {
        "planned_rotation_assessment": planned_assessment,
        "recommendations": recommendations,
    }
