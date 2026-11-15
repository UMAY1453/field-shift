"""İklim analizi modülünün girdi doğrulama testleri."""

import pytest
import json 
from datetime import datetime
from backend.climate_analysis import (
    ClimateAnalysisError,
    InsufficientClimateDataError,
    _calculate_basic_summary,
    _calculate_data_completeness,
    _calculate_dry_and_hot_metrics,
    _calculate_monthly_climate,
    _calculate_risk,
    _classify_risk_level,
    _ensure_core_data_available,
    _generate_month_keys,
    _validate_and_sort_records,
    analyze_climate,
)

def make_record(
    date: str = "2025-01-01",
    **overrides,
) -> dict:
    """Testlerde kullanılacak geçerli bir günlük kayıt oluşturur."""

    record = {
        "date": date,
        "temperature_c": 10.0,
        "temperature_min_c": 3.0,
        "temperature_max_c": 18.0,
        "precipitation_mm": 2.0,
        "relative_humidity_percent": 65.0,
        "root_zone_wetness": 0.45,
    }

    record.update(overrides)
    return record


def test_rejects_non_list_daily_records():
    """daily_records mutlaka liste olmalıdır."""

    with pytest.raises(
        ClimateAnalysisError,
        match="bir liste olmalıdır",
    ):
        analyze_climate({"date": "2025-01-01"})


def test_rejects_empty_daily_records():
    """Boş günlük kayıt listesi analiz edilemez."""

    with pytest.raises(
        ClimateAnalysisError,
        match="boş olamaz",
    ):
        analyze_climate([])


def test_rejects_invalid_date_format():
    """Tarihler tam YYYY-MM-DD biçiminde olmalıdır."""

    records = [
        make_record(date="2025-1-1"),
    ]

    with pytest.raises(
        ClimateAnalysisError,
        match="YYYY-MM-DD",
    ):
        analyze_climate(records)


def test_rejects_duplicate_dates():
    """Aynı tarih günlük kayıtlarda iki kez bulunamaz."""

    records = [
        make_record(date="2025-01-01"),
        make_record(date="2025-01-01"),
    ]

    with pytest.raises(
        ClimateAnalysisError,
        match="birden fazla kez",
    ):
        analyze_climate(records)


def test_rejects_missing_core_field():
    """Çekirdek alanlardan biri kayıtta bulunmuyorsa hata oluşur."""

    record = make_record()
    del record["precipitation_mm"]

    with pytest.raises(
        ClimateAnalysisError,
        match="çekirdek alanlar eksik",
    ):
        analyze_climate([record])


def test_rejects_nasa_fill_value():
    """Temizlenmemiş NASA -999 dolgu değeri reddedilir."""

    records = [
        make_record(temperature_c=-999),
    ]

    with pytest.raises(
        ClimateAnalysisError,
        match="dolgu değeri",
    ):
        analyze_climate(records)


def test_rejects_negative_precipitation():
    """Yağış değeri negatif olamaz."""

    records = [
        make_record(precipitation_mm=-0.1),
    ]

    with pytest.raises(
        ClimateAnalysisError,
        match="küçük olamaz",
    ):
        analyze_climate(records)


def test_rejects_humidity_above_one_hundred():
    """Bağıl nem yüzde 100 değerini aşamaz."""

    records = [
        make_record(relative_humidity_percent=100.1),
    ]

    with pytest.raises(
        ClimateAnalysisError,
        match="büyük olamaz",
    ):
        analyze_climate(records)


def test_rejects_root_zone_wetness_above_one():
    """Kök bölgesi ıslaklık oranı 1 değerini aşamaz."""

    records = [
        make_record(root_zone_wetness=1.1),
    ]

    with pytest.raises(
        ClimateAnalysisError,
        match="büyük olamaz",
    ):
        analyze_climate(records)


def test_rejects_minimum_temperature_above_maximum():
    """Minimum sıcaklık maksimum sıcaklıktan büyük olamaz."""

    records = [
        make_record(
            temperature_min_c=20.0,
            temperature_max_c=10.0,
        ),
    ]

    with pytest.raises(
        ClimateAnalysisError,
        match="minimum sıcaklık",
    ):
        analyze_climate(records)


def test_sorts_records_from_oldest_to_newest():
    """Doğrulanan kayıtlar kronolojik sıraya konur."""

    records = [
        make_record(date="2025-01-03"),
        make_record(date="2025-01-01"),
        make_record(date="2025-01-02"),
    ]

    validated_records = _validate_and_sort_records(records)

    assert [
        record["date"]
        for record in validated_records
    ] == [
        "2025-01-01",
        "2025-01-02",
        "2025-01-03",
    ]


def test_missing_enrichment_fields_become_none():
    """Zenginleştirici alanlar bulunmadığında None kabul edilir."""

    record = make_record()
    del record["relative_humidity_percent"]
    del record["root_zone_wetness"]

    validated_records = _validate_and_sort_records([record])
    validated_record = validated_records[0]

    assert validated_record["relative_humidity_percent"] is None
    assert validated_record["root_zone_wetness"] is None


def test_preserves_real_zero_precipitation():
    """Gerçek sıfır yağış değeri eksik veri olarak değerlendirilmez."""

    records = [
        make_record(precipitation_mm=0),
    ]

    validated_records = _validate_and_sort_records(records)

    assert validated_records[0]["precipitation_mm"] == 0.0


def test_validation_does_not_modify_original_record():
    """Doğrulama işlemi Kişi 2'den gelen orijinal sözlüğü değiştirmez."""

    original_record = make_record(
        precipitation_mm=0,
    )
    original_snapshot = original_record.copy()

    _validate_and_sort_records([original_record])

    assert original_record == original_snapshot
@pytest.mark.parametrize(
    "missing_field",
    [
        "temperature_c",
        "temperature_min_c",
        "temperature_max_c",
        "precipitation_mm",
    ],
)
def test_rejects_core_field_missing_for_entire_period(
    missing_field,
):
    """Bir çekirdek alan tamamen eksikse yetersiz veri hatası oluşur."""

    records = [
        make_record(date="2025-01-01"),
        make_record(date="2025-01-02"),
        make_record(date="2025-01-03"),
    ]

    for record in records:
        record[missing_field] = None

    with pytest.raises(
        InsufficientClimateDataError,
        match=missing_field,
    ):
        analyze_climate(records)


def test_allows_partially_missing_core_field():
    """Çekirdek alanda en az bir geçerli değer varsa analiz devam edebilir."""

    records = [
        make_record(
            date="2025-01-01",
            temperature_c=None,
        ),
        make_record(
            date="2025-01-02",
            temperature_c=12.0,
        ),
    ]

    validated_records = _validate_and_sort_records(records)

    # Hata oluşmaması beklenir.
    _ensure_core_data_available(validated_records)


def test_allows_completely_missing_enrichment_fields():
    """Zenginleştirici alanların tamamen eksik olması temel analizi durdurmaz."""

    records = [
        make_record(
            date="2025-01-01",
            relative_humidity_percent=None,
            root_zone_wetness=None,
        ),
        make_record(
            date="2025-01-02",
            relative_humidity_percent=None,
            root_zone_wetness=None,
        ),
    ]

    validated_records = _validate_and_sort_records(records)

    # RH2M ve GWETROOT çekirdek alan olmadığı için hata oluşmamalıdır.
    _ensure_core_data_available(validated_records)
@pytest.mark.parametrize(
    "missing_field",
    [
        "temperature_c",
        "temperature_min_c",
        "temperature_max_c",
        "precipitation_mm",
    ],
)
def test_rejects_core_field_missing_for_entire_period(
    missing_field,
):
    """Bir çekirdek alan tamamen eksikse yetersiz veri hatası oluşur."""

    records = [
        make_record(date="2025-01-01"),
        make_record(date="2025-01-02"),
        make_record(date="2025-01-03"),
    ]

    for record in records:
        record[missing_field] = None

    with pytest.raises(
        InsufficientClimateDataError,
        match=missing_field,
    ):
        analyze_climate(records)


def test_allows_partially_missing_core_field():
    """Çekirdek alanda en az bir geçerli değer varsa analiz devam edebilir."""

    records = [
        make_record(
            date="2025-01-01",
            temperature_c=None,
        ),
        make_record(
            date="2025-01-02",
            temperature_c=12.0,
        ),
    ]

    validated_records = _validate_and_sort_records(records)

    # Hata oluşmaması beklenir.
    _ensure_core_data_available(validated_records)


def test_allows_completely_missing_enrichment_fields():
    """Zenginleştirici alanların tamamen eksik olması temel analizi durdurmaz."""

    records = [
        make_record(
            date="2025-01-01",
            relative_humidity_percent=None,
            root_zone_wetness=None,
        ),
        make_record(
            date="2025-01-02",
            relative_humidity_percent=None,
            root_zone_wetness=None,
        ),
    ]

    validated_records = _validate_and_sort_records(records)

    # RH2M ve GWETROOT çekirdek alan olmadığı için hata oluşmamalıdır.
    _ensure_core_data_available(validated_records)
def test_calculates_basic_climate_summary():
    """Ortalama, minimum, maksimum sıcaklık ve toplam yağış hesaplanır."""

    records = [
        make_record(
            date="2025-01-01",
            temperature_c=10.0,
            temperature_min_c=3.0,
            temperature_max_c=20.0,
            precipitation_mm=0.0,
        ),
        make_record(
            date="2025-01-02",
            temperature_c=12.0,
            temperature_min_c=5.0,
            temperature_max_c=36.0,
            precipitation_mm=0.5,
        ),
        make_record(
            date="2025-01-03",
            temperature_c=14.0,
            temperature_min_c=7.0,
            temperature_max_c=25.0,
            precipitation_mm=5.0,
        ),
    ]

    validated_records = _validate_and_sort_records(records)
    _ensure_core_data_available(validated_records)

    summary = _calculate_basic_summary(validated_records)

    assert summary == {
        "average_temperature_c": 12.0,
        "minimum_temperature_c": 3.0,
        "maximum_temperature_c": 36.0,
        "total_precipitation_mm": 5.5,
    }

def test_basic_summary_ignores_null_values():
    """None değerler özet hesaplamalarına katılmaz."""

    records = [
        make_record(
            date="2025-01-01",
            temperature_c=10.0,
            temperature_min_c=None,
            temperature_max_c=20.0,
            precipitation_mm=0.0,
        ),
        make_record(
            date="2025-01-02",
            temperature_c=None,
            temperature_min_c=2.0,
            temperature_max_c=None,
            precipitation_mm=None,
        ),
        make_record(
            date="2025-01-03",
            temperature_c=14.0,
            temperature_min_c=4.0,
            temperature_max_c=36.0,
            precipitation_mm=5.5,
        ),
    ]

    validated_records = _validate_and_sort_records(records)
    _ensure_core_data_available(validated_records)

    summary = _calculate_basic_summary(validated_records)

    assert summary == {
        "average_temperature_c": 12.0,
        "minimum_temperature_c": 2.0,
        "maximum_temperature_c": 36.0,
        "total_precipitation_mm": 5.5,
    }

def test_basic_summary_preserves_zero_precipitation_total():
    """Geçerli sıfır yağış değerleri toplamda sıfır olarak korunur."""

    records = [
        make_record(
            date="2025-01-01",
            precipitation_mm=0.0,
        ),
        make_record(
            date="2025-01-02",
            precipitation_mm=0.0,
        ),
    ]

    validated_records = _validate_and_sort_records(records)
    _ensure_core_data_available(validated_records)

    summary = _calculate_basic_summary(validated_records)

    assert summary["total_precipitation_mm"] == 0.0   
def test_counts_dry_and_hot_days_at_thresholds():
    """Kuru ve sıcak gün eşikleri sınır değerlerde doğru uygulanır."""

    records = [
        make_record(
            date="2025-01-01",
            precipitation_mm=0.0,
            temperature_max_c=34.9,
        ),
        make_record(
            date="2025-01-02",
            precipitation_mm=0.99,
            temperature_max_c=35.0,
        ),
        make_record(
            date="2025-01-03",
            precipitation_mm=1.0,
            temperature_max_c=36.0,
        ),
        make_record(
            date="2025-01-04",
            precipitation_mm=None,
            temperature_max_c=None,
        ),
    ]

    validated_records = _validate_and_sort_records(records)
    metrics = _calculate_dry_and_hot_metrics(validated_records)

    assert metrics["dry_days"] == 2
    assert metrics["hot_days"] == 2

def test_calculates_longest_dry_spell():
    """Arka arkaya gelen en uzun kuru gün dizisi bulunur."""

    records = [
        make_record(
            date="2025-01-01",
            precipitation_mm=0.0,
        ),
        make_record(
            date="2025-01-02",
            precipitation_mm=0.5,
        ),
        make_record(
            date="2025-01-03",
            precipitation_mm=2.0,
        ),
        make_record(
            date="2025-01-04",
            precipitation_mm=0.0,
        ),
        make_record(
            date="2025-01-05",
            precipitation_mm=0.2,
        ),
        make_record(
            date="2025-01-06",
            precipitation_mm=0.8,
        ),
    ]

    validated_records = _validate_and_sort_records(records)
    metrics = _calculate_dry_and_hot_metrics(validated_records)

    assert metrics["dry_days"] == 5
    assert metrics["longest_dry_spell_days"] == 3

def test_null_precipitation_breaks_dry_spell():
    """Yağışın bilinmediği gün kesintisiz kuru dönem zincirini keser."""

    records = [
        make_record(
            date="2025-01-01",
            precipitation_mm=0.0,
        ),
        make_record(
            date="2025-01-02",
            precipitation_mm=None,
        ),
        make_record(
            date="2025-01-03",
            precipitation_mm=0.0,
        ),
    ]

    validated_records = _validate_and_sort_records(records)
    metrics = _calculate_dry_and_hot_metrics(validated_records)

    assert metrics["dry_days"] == 2
    assert metrics["longest_dry_spell_days"] == 1

def test_date_gap_breaks_dry_spell():
    """Takvimde eksik gün bulunması kesintisiz kuru dönemi keser."""

    records = [
        make_record(
            date="2025-01-01",
            precipitation_mm=0.0,
        ),
        make_record(
            date="2025-01-02",
            precipitation_mm=0.0,
        ),
        make_record(
            date="2025-01-04",
            precipitation_mm=0.0,
        ),
    ]

    validated_records = _validate_and_sort_records(records)
    metrics = _calculate_dry_and_hot_metrics(validated_records)

    assert metrics["dry_days"] == 3
    assert metrics["longest_dry_spell_days"] == 2 
def test_complete_core_data_is_one_hundred_percent():
    """Eksiksiz çekirdek ölçümler yüzde 100 tamlık üretir."""

    records = [
        make_record(date="2025-01-01"),
        make_record(date="2025-01-02"),
    ]

    validated_records = _validate_and_sort_records(records)

    assert _calculate_data_completeness(validated_records) == 100.0


def test_missing_core_value_reduces_completeness():
    """Günlük eksik çekirdek ölçüm veri tamlığını düşürür."""

    records = [
        make_record(date="2025-01-01"),
        make_record(
            date="2025-01-02",
            temperature_c=None,
        ),
    ]

    validated_records = _validate_and_sort_records(records)

    # 2 gün × 4 alan = 8 beklenen ölçüm.
    # Bir ölçüm eksik olduğu için 7 / 8 × 100 = 87.5.
    assert _calculate_data_completeness(validated_records) == 87.5


def test_missing_calendar_day_reduces_completeness():
    """Takvimde tamamen bulunmayan gün dört eksik ölçüm olarak değerlendirilir."""

    records = [
        make_record(date="2025-01-01"),
        make_record(date="2025-01-03"),
    ]

    validated_records = _validate_and_sort_records(records)

    # 1–3 Ocak arasında 3 gün ve 12 beklenen çekirdek ölçüm vardır.
    # İki tam kayıt 8 mevcut ölçüm sağlar: 8 / 12 × 100 = 66.7.
    assert _calculate_data_completeness(validated_records) == 66.7


def test_missing_enrichment_values_do_not_reduce_completeness():
    """RH2M ve GWETROOT eksikliği çekirdek tamlık oranını etkilemez."""

    records = [
        make_record(
            date="2025-01-01",
            relative_humidity_percent=None,
            root_zone_wetness=None,
        ),
        make_record(
            date="2025-01-02",
            relative_humidity_percent=None,
            root_zone_wetness=None,
        ),
    ]

    validated_records = _validate_and_sort_records(records)

    assert _calculate_data_completeness(validated_records) == 100.0
def test_generates_month_keys_across_year_boundary():
    """Ay anahtarları yıl değişimini doğru yönetir."""

    first_date = datetime.strptime(
        "2024-11-15",
        "%Y-%m-%d",
    ).date()
    last_date = datetime.strptime(
        "2025-02-10",
        "%Y-%m-%d",
    ).date()

    assert _generate_month_keys(first_date, last_date) == [
        "2024-11",
        "2024-12",
        "2025-01",
        "2025-02",
    ]


def test_calculates_monthly_climate():
    """Günlük sıcaklık ve yağış değerleri aya göre gruplanır."""

    records = [
        make_record(
            date="2025-01-01",
            temperature_c=10.0,
            precipitation_mm=1.0,
        ),
        make_record(
            date="2025-01-02",
            temperature_c=14.0,
            precipitation_mm=2.0,
        ),
        make_record(
            date="2025-02-01",
            temperature_c=20.0,
            precipitation_mm=0.0,
        ),
    ]

    validated_records = _validate_and_sort_records(records)
    monthly_climate = _calculate_monthly_climate(
        validated_records
    )

    assert monthly_climate == [
        {
            "month": "2025-01",
            "average_temperature_c": 12.0,
            "precipitation_mm": 3.0,
        },
        {
            "month": "2025-02",
            "average_temperature_c": 20.0,
            "precipitation_mm": 0.0,
        },
    ]


def test_monthly_climate_ignores_partial_null_values():
    """Aylık hesaplamalarda None değerler dışarıda bırakılır."""

    records = [
        make_record(
            date="2025-01-01",
            temperature_c=10.0,
            precipitation_mm=1.0,
        ),
        make_record(
            date="2025-01-02",
            temperature_c=None,
            precipitation_mm=None,
        ),
    ]

    validated_records = _validate_and_sort_records(records)
    monthly_climate = _calculate_monthly_climate(
        validated_records
    )

    assert monthly_climate == [
        {
            "month": "2025-01",
            "average_temperature_c": 10.0,
            "precipitation_mm": 1.0,
        }
    ]


def test_completely_missing_month_is_kept_with_null_values():
    """Takvimde kaydı bulunmayan ay listede null değerlerle korunur."""

    records = [
        make_record(
            date="2025-01-01",
            temperature_c=10.0,
            precipitation_mm=5.0,
        ),
        make_record(
            date="2025-03-01",
            temperature_c=15.0,
            precipitation_mm=8.0,
        ),
    ]

    validated_records = _validate_and_sort_records(records)
    monthly_climate = _calculate_monthly_climate(
        validated_records
    )

    assert monthly_climate == [
        {
            "month": "2025-01",
            "average_temperature_c": 10.0,
            "precipitation_mm": 5.0,
        },
        {
            "month": "2025-02",
            "average_temperature_c": None,
            "precipitation_mm": None,
        },
        {
            "month": "2025-03",
            "average_temperature_c": 15.0,
            "precipitation_mm": 8.0,
        },
    ]
def test_calculates_low_risk():
    """Düşük göstergeler low risk üretir."""

    records = [
        make_record(
            date=f"2025-01-{day:02d}",
            precipitation_mm=2.0,
            temperature_max_c=25.0,
        )
        for day in range(1, 11)
    ]

    validated_records = _validate_and_sort_records(records)

    summary = {
        "dry_days": 0,
        "longest_dry_spell_days": 0,
        "hot_days": 0,
        "data_completeness_percent": 100.0,
    }

    risk = _calculate_risk(
        summary,
        validated_records,
    )

    assert risk["score"] == 0
    assert risk["level"] == "low"
    assert risk["reasons"] == [
        "Belirgin bir iklimsel su stresi göstergesi tespit edilmedi."
    ]


def test_calculates_medium_risk():
    """Orta düzey göstergeler medium risk üretir."""

    records = [
        make_record(
            date=f"2025-01-{day:02d}",
            precipitation_mm=0.0 if day <= 5 else 2.0,
            temperature_max_c=36.0 if day == 1 else 25.0,
        )
        for day in range(1, 11)
    ]

    validated_records = _validate_and_sort_records(records)

    summary = {
        "dry_days": 5,
        "longest_dry_spell_days": 5,
        "hot_days": 1,
        "data_completeness_percent": 100.0,
    }

    risk = _calculate_risk(
        summary,
        validated_records,
    )

    # %50 kuru gün = 15 puan.
    # %10 sıcak gün = 25 puan.
    # 5 günlük kuru dönem = 0 puan.
    assert risk["score"] == 40
    assert risk["level"] == "medium"


def test_calculates_high_risk():
    """Yüksek göstergeler high risk üretir."""

    records = [
        make_record(
            date=f"2025-01-{day:02d}",
            precipitation_mm=0.0 if day <= 8 else 2.0,
            temperature_max_c=36.0 if day == 1 else 25.0,
        )
        for day in range(1, 11)
    ]

    validated_records = _validate_and_sort_records(records)

    summary = {
        "dry_days": 8,
        "longest_dry_spell_days": 30,
        "hot_days": 1,
        "data_completeness_percent": 100.0,
    }

    risk = _calculate_risk(
        summary,
        validated_records,
    )

    # %80 kuru gün = 40 puan.
    # 30 günlük kuru dönem = 35 puan.
    # %10 sıcak gün = 25 puan.
    assert risk["score"] == 100
    assert risk["level"] == "high"


def test_low_completeness_adds_warning_without_risk_points():
    """Düşük veri tamlığı gerekçe ekler fakat iklim riskini artırmaz."""

    records = [
        make_record(
            date="2025-01-01",
            precipitation_mm=2.0,
            temperature_max_c=25.0,
        )
    ]

    validated_records = _validate_and_sort_records(records)

    summary = {
        "dry_days": 0,
        "longest_dry_spell_days": 0,
        "hot_days": 0,
        "data_completeness_percent": 75.0,
    }

    risk = _calculate_risk(
        summary,
        validated_records,
    )

    assert risk["score"] == 0
    assert risk["level"] == "low"
    assert any(
        "Veri tamlığı" in reason
        for reason in risk["reasons"]
    )


def test_analyze_climate_returns_complete_json_compatible_result():
    """Ana fonksiyon sözleşmedeki üç bölümü JSON uyumlu döndürür."""

    records = [
        make_record(
            date="2025-01-01",
            temperature_c=10.0,
            temperature_min_c=2.0,
            temperature_max_c=20.0,
            precipitation_mm=0.0,
        ),
        make_record(
            date="2025-01-02",
            temperature_c=12.0,
            temperature_min_c=4.0,
            temperature_max_c=36.0,
            precipitation_mm=2.0,
        ),
    ]

    result = analyze_climate(records)

    assert set(result) == {
        "summary",
        "risk",
        "monthly_climate",
    }

    assert result["summary"] == {
        "average_temperature_c": 11.0,
        "minimum_temperature_c": 2.0,
        "maximum_temperature_c": 36.0,
        "total_precipitation_mm": 2.0,
        "dry_days": 1,
        "longest_dry_spell_days": 1,
        "hot_days": 1,
        "data_completeness_percent": 100.0,
    }

    assert result["monthly_climate"] == [
        {
            "month": "2025-01",
            "average_temperature_c": 11.0,
            "precipitation_mm": 2.0,
        }
    ]

    # allow_nan=False, NaN ve Infinity gibi geçersiz JSON sayılarını reddeder.
    serialized_result = json.dumps(
        result,
        ensure_ascii=False,
        allow_nan=False,
    )

    assert serialized_result
@pytest.mark.parametrize(
    ("score", "expected_level"),
    [
        (0, "low"),
        (33, "low"),
        (34, "medium"),
        (66, "medium"),
        (67, "high"),
        (100, "high"),
    ],
)
def test_classifies_risk_score_boundaries(
    score: int,
    expected_level: str,
):
    """Risk seviyelerinin kesin puan sınırlarını doğrular."""

    assert _classify_risk_level(score) == expected_level
def test_keeps_month_when_temperature_data_is_missing():
    """Bir ayda sıcaklık yoksa ay korunur ve sıcaklık None döner."""

    records = [
        make_record(
            date="2025-01-01",
            temperature_c=None,
            precipitation_mm=5.0,
        ),
        make_record(
            date="2025-02-01",
            temperature_c=12.0,
            precipitation_mm=3.0,
        ),
    ]

    result = analyze_climate(records)

    assert result["monthly_climate"][0] == {
        "month": "2025-01",
        "average_temperature_c": None,
        "precipitation_mm": 5.0,
    }


def test_keeps_month_when_precipitation_data_is_missing():
    """Bir ayda yağış yoksa ay korunur ve yağış None döner."""

    records = [
        make_record(
            date="2025-01-01",
            temperature_c=10.0,
            precipitation_mm=None,
        ),
        make_record(
            date="2025-02-01",
            temperature_c=12.0,
            precipitation_mm=3.0,
        ),
    ]

    result = analyze_climate(records)

    assert result["monthly_climate"][0] == {
        "month": "2025-01",
        "average_temperature_c": 10.0,
        "precipitation_mm": None,
    }