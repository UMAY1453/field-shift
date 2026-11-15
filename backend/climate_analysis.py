"""Field Shift iklim analizi ve risk hesaplama modülü.

Bu modül, NASA veri servisi tarafından normalize edilmiş günlük iklim
kayıtlarını analiz eder. Modül ağ isteği veya FastAPI HTTP hatası üretmez.
"""
from datetime import date, datetime, timedelta
import math
from typing import Any


# CONTRACTS.md içinde belirlenen prototip eşikleri.
DRY_DAY_THRESHOLD_MM = 1.0
HOT_DAY_THRESHOLD_C = 35.0

# Risk seviyelerini belirleyen üst sınırlar.
RISK_LOW_MAX = 33
RISK_MEDIUM_MAX = 66


# Analiz için zorunlu çekirdek ölçüm alanları.
CORE_FIELDS = (
    "temperature_c",
    "temperature_min_c",
    "temperature_max_c",
    "precipitation_mm",
)

# Temel analizi zenginleştiren fakat zorunlu olmayan alanlar.
ENRICHMENT_FIELDS = (
    "relative_humidity_percent",
    "root_zone_wetness",
)


class ClimateAnalysisError(ValueError):
    """Geçersiz iklim kayıtları için oluşturulan genel analiz hatası."""


class InsufficientClimateDataError(ClimateAnalysisError):
    """Çekirdek iklim verileri analiz için yetersiz olduğunda oluşturulur."""


def _validate_date(value: Any, record_index: int) -> str:
    """Tarih değerini doğrular ve standart metin biçiminde döndürür."""

    if not isinstance(value, str):
        raise ClimateAnalysisError(
            f"{record_index}. kaydın date alanı metin olmalıdır."
        )

    try:
        parsed_date = datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as error:
        raise ClimateAnalysisError(
            f"{record_index}. kaydın date alanı geçersiz: {value!r}."
        ) from error

    # strptime bazı sistemlerde sıfır eklenmemiş tarihleri de kabul edebilir.
    # isoformat karşılaştırması tam YYYY-MM-DD biçimini zorunlu kılar.
    if parsed_date.isoformat() != value:
        raise ClimateAnalysisError(
            f"{record_index}. kaydın date alanı YYYY-MM-DD biçiminde olmalıdır."
        )

    return value


def _normalize_numeric_value(
    value: Any,
    *,
    field_name: str,
    record_date: str,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    """Sayısal bir alanı doğrular ve float ya da None olarak döndürür."""

    if value is None:
        return None

    # Python'da bool, int sınıfının alt türüdür. Bu nedenle True ve False
    # değerlerini ayrıca reddediyoruz.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ClimateAnalysisError(
            f"{record_date} tarihindeki {field_name} alanı "
            "sayı veya null olmalıdır."
        )

    normalized_value = float(value)

    if not math.isfinite(normalized_value):
        raise ClimateAnalysisError(
            f"{record_date} tarihindeki {field_name} alanı "
            "sonlu bir sayı olmalıdır."
        )

    # NASA POWER tarafından eksik ölçümler için kullanılan dolgu değeri,
    # gerçek ölçüm olarak analize katılmamalıdır.
    if normalized_value == -999.0:
        raise ClimateAnalysisError(
            f"{record_date} tarihindeki {field_name} alanında "
            "temizlenmemiş NASA dolgu değeri -999 bulundu."
        )

    if minimum is not None and normalized_value < minimum:
        raise ClimateAnalysisError(
            f"{record_date} tarihindeki {field_name} alanı "
            f"{minimum} değerinden küçük olamaz."
        )

    if maximum is not None and normalized_value > maximum:
        raise ClimateAnalysisError(
            f"{record_date} tarihindeki {field_name} alanı "
            f"{maximum} değerinden büyük olamaz."
        )

    return normalized_value


def _validate_and_sort_records(
    daily_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Günlük kayıtları doğrular, kopyalar ve tarih sırasına koyar."""

    if not isinstance(daily_records, list):
        raise ClimateAnalysisError(
            "daily_records bir liste olmalıdır."
        )

    if not daily_records:
        raise ClimateAnalysisError(
            "daily_records boş olamaz."
        )

    validated_records: list[dict[str, Any]] = []
    seen_dates: set[str] = set()

    for record_index, record in enumerate(daily_records):
        if not isinstance(record, dict):
            raise ClimateAnalysisError(
                f"{record_index}. günlük kayıt bir sözlük olmalıdır."
            )

        if "date" not in record:
            raise ClimateAnalysisError(
                f"{record_index}. günlük kayıtta date alanı bulunmalıdır."
            )

        record_date = _validate_date(
            record["date"],
            record_index,
        )

        if record_date in seen_dates:
            raise ClimateAnalysisError(
                f"Aynı tarih birden fazla kez bulunamaz: {record_date}."
            )

        seen_dates.add(record_date)

        missing_core_fields = [
            field_name
            for field_name in CORE_FIELDS
            if field_name not in record
        ]

        if missing_core_fields:
            missing_fields_text = ", ".join(missing_core_fields)

            raise ClimateAnalysisError(
                f"{record_date} tarihindeki kayıtta çekirdek alanlar eksik: "
                f"{missing_fields_text}."
            )

        # Girdi sözlüğünü doğrudan değiştirmemek için bir kopya oluşturuyoruz.
        normalized_record = dict(record)
        normalized_record["date"] = record_date

        normalized_record["temperature_c"] = _normalize_numeric_value(
            record["temperature_c"],
            field_name="temperature_c",
            record_date=record_date,
        )

        normalized_record["temperature_min_c"] = _normalize_numeric_value(
            record["temperature_min_c"],
            field_name="temperature_min_c",
            record_date=record_date,
        )

        normalized_record["temperature_max_c"] = _normalize_numeric_value(
            record["temperature_max_c"],
            field_name="temperature_max_c",
            record_date=record_date,
        )

        normalized_record["precipitation_mm"] = _normalize_numeric_value(
            record["precipitation_mm"],
            field_name="precipitation_mm",
            record_date=record_date,
            minimum=0.0,
        )

        # Zenginleştirici alanlar kayıtta bulunmazsa None kabul edilir.
        normalized_record["relative_humidity_percent"] = (
            _normalize_numeric_value(
                record.get("relative_humidity_percent"),
                field_name="relative_humidity_percent",
                record_date=record_date,
                minimum=0.0,
                maximum=100.0,
            )
        )

        normalized_record["root_zone_wetness"] = _normalize_numeric_value(
            record.get("root_zone_wetness"),
            field_name="root_zone_wetness",
            record_date=record_date,
            minimum=0.0,
            maximum=1.0,
        )

        minimum_temperature = normalized_record["temperature_min_c"]
        maximum_temperature = normalized_record["temperature_max_c"]

        if (
            minimum_temperature is not None
            and maximum_temperature is not None
            and minimum_temperature > maximum_temperature
        ):
            raise ClimateAnalysisError(
                f"{record_date} tarihinde minimum sıcaklık, "
                "maksimum sıcaklıktan büyük olamaz."
            )

        validated_records.append(normalized_record)

    # YYYY-MM-DD biçimindeki tarihler metin olarak da kronolojik sıralanır.
    validated_records.sort(
        key=lambda record: record["date"]
    )

    return validated_records
def _ensure_core_data_available(
    validated_records: list[dict[str, Any]],
) -> None:
    """Her çekirdek alanda en az bir geçerli ölçüm bulunduğunu doğrular."""

    unavailable_fields = [
        field_name
        for field_name in CORE_FIELDS
        if not any(
            record[field_name] is not None
            for record in validated_records
        )
    ]

    if unavailable_fields:
        unavailable_fields_text = ", ".join(unavailable_fields)

        raise InsufficientClimateDataError(
            "Bütün dönem boyunca geçerli ölçümü bulunmayan "
            f"çekirdek alanlar: {unavailable_fields_text}."
        )
def _ensure_core_data_available(
    validated_records: list[dict[str, Any]],
) -> None:
    """Her çekirdek alanda en az bir geçerli ölçüm bulunduğunu doğrular."""

    unavailable_fields = [
        field_name
        for field_name in CORE_FIELDS
        if not any(
            record[field_name] is not None
            for record in validated_records
        )
    ]

    if unavailable_fields:
        unavailable_fields_text = ", ".join(unavailable_fields)

        raise InsufficientClimateDataError(
            "Bütün dönem boyunca geçerli ölçümü bulunmayan "
            f"çekirdek alanlar: {unavailable_fields_text}."
        )
def _collect_valid_values(
    validated_records: list[dict[str, Any]],
    field_name: str,
) -> list[float]:
    """Bir alandaki None olmayan geçerli sayısal değerleri toplar."""

    return [
        record[field_name]
        for record in validated_records
        if record[field_name] is not None
    ]


def _calculate_basic_summary(
    validated_records: list[dict[str, Any]],
) -> dict[str, float]:
    """Temel sıcaklık ve yağış özetini hesaplar."""

    average_temperatures = _collect_valid_values(
        validated_records,
        "temperature_c",
    )
    minimum_temperatures = _collect_valid_values(
        validated_records,
        "temperature_min_c",
    )
    maximum_temperatures = _collect_valid_values(
        validated_records,
        "temperature_max_c",
    )
    precipitation_values = _collect_valid_values(
        validated_records,
        "precipitation_mm",
    )

    average_temperature = (
        sum(average_temperatures)
        / len(average_temperatures)
    )

    minimum_temperature = min(minimum_temperatures)
    maximum_temperature = max(maximum_temperatures)
    total_precipitation = sum(precipitation_values)

    return {
        "average_temperature_c": round(average_temperature, 1),
        "minimum_temperature_c": round(minimum_temperature, 1),
        "maximum_temperature_c": round(maximum_temperature, 1),
        "total_precipitation_mm": round(total_precipitation, 1),
    }
def _calculate_dry_and_hot_metrics(
    validated_records: list[dict[str, Any]],
) -> dict[str, int]:
    """Kuru gün, sıcak gün ve en uzun kuru dönem metriklerini hesaplar."""

    dry_days = 0
    hot_days = 0
    current_dry_spell = 0
    longest_dry_spell = 0
    previous_date = None

    for record in validated_records:
        current_date = datetime.strptime(
            record["date"],
            "%Y-%m-%d",
        ).date()

        precipitation = record["precipitation_mm"]
        maximum_temperature = record["temperature_max_c"]

        dates_are_consecutive = (
            previous_date is not None
            and current_date - previous_date == timedelta(days=1)
        )

        is_dry_day = (
            precipitation is not None
            and precipitation < DRY_DAY_THRESHOLD_MM
        )

        if is_dry_day:
            dry_days += 1

            # Bir önceki kayıt var fakat takvimde ardışık değilse
            # önceki kuru dönem devam edemez.
            if previous_date is not None and not dates_are_consecutive:
                current_dry_spell = 0

            current_dry_spell += 1
            longest_dry_spell = max(
                longest_dry_spell,
                current_dry_spell,
            )
        else:
            # Yağışlı veya yağışı bilinmeyen gün kuru dönemi keser.
            current_dry_spell = 0

        if (
            maximum_temperature is not None
            and maximum_temperature >= HOT_DAY_THRESHOLD_C
        ):
            hot_days += 1

        previous_date = current_date

    return {
        "dry_days": dry_days,
        "longest_dry_spell_days": longest_dry_spell,
        "hot_days": hot_days,
    }
def _calculate_data_completeness(
    validated_records: list[dict[str, Any]],
) -> float:
    """Çekirdek iklim ölçümlerinin veri tamlık yüzdesini hesaplar."""

    first_date = datetime.strptime(
        validated_records[0]["date"],
        "%Y-%m-%d",
    ).date()

    last_date = datetime.strptime(
        validated_records[-1]["date"],
        "%Y-%m-%d",
    ).date()

    expected_day_count = (
        last_date - first_date
    ).days + 1

    expected_measurement_count = (
        expected_day_count * len(CORE_FIELDS)
    )

    available_measurement_count = sum(
        1
        for record in validated_records
        for field_name in CORE_FIELDS
        if record[field_name] is not None
    )

    completeness_percent = (
        available_measurement_count
        / expected_measurement_count
        * 100
    )

    return round(completeness_percent, 1)
def _generate_month_keys(
    first_date: date,
    last_date: date,
) -> list[str]:
    """İlk ve son tarih arasındaki bütün YYYY-MM değerlerini üretir."""

    month_keys: list[str] = []

    current_year = first_date.year
    current_month = first_date.month

    while (
        current_year < last_date.year
        or (
            current_year == last_date.year
            and current_month <= last_date.month
        )
    ):
        month_keys.append(
            f"{current_year:04d}-{current_month:02d}"
        )

        if current_month == 12:
            current_year += 1
            current_month = 1
        else:
            current_month += 1

    return month_keys
def _calculate_monthly_climate(
    validated_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Günlük kayıtları aylık sıcaklık ve yağış özetlerine dönüştürür."""

    first_date = datetime.strptime(
        validated_records[0]["date"],
        "%Y-%m-%d",
    ).date()

    last_date = datetime.strptime(
        validated_records[-1]["date"],
        "%Y-%m-%d",
    ).date()

    monthly_values = {
        month_key: {
            "temperatures": [],
            "precipitation": [],
        }
        for month_key in _generate_month_keys(
            first_date,
            last_date,
        )
    }

    for record in validated_records:
        month_key = record["date"][:7]

        temperature = record["temperature_c"]
        precipitation = record["precipitation_mm"]

        if temperature is not None:
            monthly_values[month_key]["temperatures"].append(
                temperature
            )

        if precipitation is not None:
            monthly_values[month_key]["precipitation"].append(
                precipitation
            )

    monthly_climate: list[dict[str, Any]] = []

    for month_key, values in monthly_values.items():
        temperatures = values["temperatures"]
        precipitation_values = values["precipitation"]

        if temperatures:
            average_temperature = round(
                sum(temperatures) / len(temperatures),
                1,
            )
        else:
            average_temperature = None

        if precipitation_values:
            total_precipitation = round(
                sum(precipitation_values),
                1,
            )
        else:
            total_precipitation = None

        monthly_climate.append(
            {
                "month": month_key,
                "average_temperature_c": average_temperature,
                "precipitation_mm": total_precipitation,
            }
        )

    return monthly_climate
def _score_dry_day_ratio(dry_day_ratio: float) -> int:
    """Kuru gün oranını 0–40 arasında puanlar."""

    if dry_day_ratio >= 0.80:
        return 40

    if dry_day_ratio >= 0.60:
        return 30

    if dry_day_ratio >= 0.40:
        return 15

    return 0


def _score_longest_dry_spell(
    longest_dry_spell_days: int,
) -> int:
    """En uzun kuru dönemi 0–35 arasında puanlar."""

    if longest_dry_spell_days >= 30:
        return 35

    if longest_dry_spell_days >= 21:
        return 30

    if longest_dry_spell_days >= 14:
        return 20

    if longest_dry_spell_days >= 7:
        return 10

    return 0


def _score_hot_day_ratio(hot_day_ratio: float) -> int:
    """Sıcak gün oranını 0–25 arasında puanlar."""

    if hot_day_ratio >= 0.10:
        return 25

    if hot_day_ratio >= 0.05:
        return 20

    if hot_day_ratio >= 0.01:
        return 10

    return 0


def _classify_risk_level(score: int) -> str:
    """Risk skorunu low, medium veya high olarak sınıflandırır."""

    if score <= RISK_LOW_MAX:
        return "low"

    if score <= RISK_MEDIUM_MAX:
        return "medium"

    return "high"


def _calculate_risk(
    summary: dict[str, Any],
    validated_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """İklim özeti ve geçerli gün sayılarına göre risk sonucu üretir."""

    valid_precipitation_day_count = sum(
        1
        for record in validated_records
        if record["precipitation_mm"] is not None
    )

    valid_maximum_temperature_day_count = sum(
        1
        for record in validated_records
        if record["temperature_max_c"] is not None
    )

    dry_day_ratio = (
        summary["dry_days"]
        / valid_precipitation_day_count
    )

    hot_day_ratio = (
        summary["hot_days"]
        / valid_maximum_temperature_day_count
    )

    dry_day_score = _score_dry_day_ratio(
        dry_day_ratio
    )
    dry_spell_score = _score_longest_dry_spell(
        summary["longest_dry_spell_days"]
    )
    hot_day_score = _score_hot_day_ratio(
        hot_day_ratio
    )

    score = min(
        100,
        dry_day_score
        + dry_spell_score
        + hot_day_score,
    )

    reasons: list[str] = []

    if dry_day_score > 0:
        reasons.append(
            "Geçerli yağış günlerinin "
            f"%{round(dry_day_ratio * 100, 1)} kadarı "
            "kuru gün olarak sınıflandırıldı."
        )

    if dry_spell_score > 0:
        reasons.append(
            "En uzun kuru dönem "
            f"{summary['longest_dry_spell_days']} gün sürdü."
        )

    if hot_day_score > 0:
        reasons.append(
            f"{summary['hot_days']} sıcak gün tespit edildi."
        )

    if summary["data_completeness_percent"] < 90.0:
        reasons.append(
            "Veri tamlığı "
            f"%{summary['data_completeness_percent']}; "
            "sonuçlar eksik ölçümler içeriyor."
        )

    if not reasons:
        reasons.append(
            "Belirgin bir iklimsel su stresi göstergesi "
            "tespit edilmedi."
        )

    return {
        "level": _classify_risk_level(score),
        "score": score,
        "reasons": reasons,
    }
def analyze_climate(
    daily_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """Normalize edilmiş günlük kayıtlardan iklim sonucu üretir.

    Args:
        daily_records:
            Kişi 2'nin NASA verisinden ürettiği JSON uyumlu günlük
            kayıtların listesi.

    Returns:
        ``summary``, ``risk`` ve ``monthly_climate`` bölümlerini içeren,
        JSON uyumlu bir sözlük.

    Raises:
        ClimateAnalysisError:
            Girdi yapısı, alan tipi veya tarih bilgisi geçersiz olduğunda.
        InsufficientClimateDataError:
            Çekirdek ölçüm alanlarından biri bütün dönem boyunca
            kullanılamadığında.
    """

    validated_records = _validate_and_sort_records(daily_records)
    _ensure_core_data_available(validated_records)

    summary = _calculate_basic_summary(validated_records)
    summary.update(
        _calculate_dry_and_hot_metrics(validated_records)
    )
    summary["data_completeness_percent"] = (
        _calculate_data_completeness(validated_records)
    )

    monthly_climate = _calculate_monthly_climate(
        validated_records
    )

    risk = _calculate_risk(
        summary,
        validated_records,
    )

    return {
        "summary": summary,
        "risk": risk,
        "monthly_climate": monthly_climate,
    }