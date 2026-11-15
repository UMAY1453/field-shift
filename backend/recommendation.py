"""Ürün rotasyonu değerlendirme ve öneri yardımcıları."""

import json
from datetime import date
from pathlib import Path


CROPS_PATH = Path(__file__).with_name("data") / "crops.json"


class RecommendationError(Exception):
    """Rotasyon modülündeki hataların temel sınıfı."""


class InvalidCropSelectionError(RecommendationError):
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


def calculate_annual_precipitation_mm(climate_result: dict) -> float:
    """Analiz dönemi toplam yağışını yıllık ortalama yağışa dönüştürür."""

    try:
        metadata = climate_result["metadata"]
        summary = climate_result["summary"]
        start_date = date.fromisoformat(metadata["start_date"])
        end_date = date.fromisoformat(metadata["end_date"])
        total_precipitation = summary["total_precipitation_mm"]
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidClimateResultError(
            "İklim sonucu geçerli analiz tarihlerini ve toplam yağışı içermelidir."
        ) from exc

    if end_date < start_date:
        raise InvalidClimateResultError(
            "İklim analizinin end_date değeri start_date değerinden önce olamaz."
        )
    if (
        isinstance(total_precipitation, bool)
        or not isinstance(total_precipitation, (int, float))
        or total_precipitation < 0
    ):
        raise InvalidClimateResultError(
            "total_precipitation_mm sıfır veya daha büyük bir sayı olmalıdır."
        )

    inclusive_day_count = (end_date - start_date).days + 1
    analysis_years = inclusive_day_count / 365.2425
    return total_precipitation / analysis_years


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
