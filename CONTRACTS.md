# Field Shift — Teknik Sözleşmeler

## 1. Amaç

Bu dosya frontend, NASA veri servisi, iklim analizi ve ürün rotasyonu modülleri arasındaki ortak veri sözleşmelerini tanımlar.

Ekip üyeleri kendi modüllerini bu sözleşmelere uygun geliştirmelidir. Bir alan adı veya veri yapısı değiştirilmeden önce ekip bilgilendirilmeli ve bu dosya güncellenmelidir.

---

## 2. Genel Kurallar

- API, JSON alır ve JSON döndürür.
- JSON alan adlarında `snake_case` kullanılır.
- Tarihler `YYYY-MM-DD` formatında gönderilir.
- Sıcaklık değerleri santigrat derece (`°C`) olarak kullanılır.
- Yağış değerleri milimetre (`mm`) olarak kullanılır.
- Skorlar `0–100` arasında tutulur.
- Eksik sayısal NASA verileri `null` olarak temsil edilir.
- Kullanıcıya gösterilen açıklamalar açık ve anlaşılır olmalıdır.
- Bilimsel kesinliği olmayan sonuçlar kesin öneri gibi sunulmamalıdır.

---

## 3. Yerel API Adresi

Backend varsayılan olarak aşağıdaki adreste çalışır:

```text
http://127.0.0.1:8000
```

Frontend bütün backend isteklerini `/api` ile başlayan adreslere gönderir.

Örnek:

```text
http://127.0.0.1:8000/api/health
```

---

## 4. Sağlık Kontrolü

### İstek

```http
GET /api/health
```

### Başarılı cevap

```json
{
  "status": "ok",
  "service": "field-shift-api"
}
```

### Kullanım amacı

Frontend ve geliştiriciler backend servisinin çalışıp çalışmadığını bu adres üzerinden kontrol eder.

---

## 5. Ürün Listesi

### İstek

```http
GET /api/crops
```

### Başarılı cevap

```json
{
  "crops": [
    {
      "id": "wheat",
      "name": "Buğday",
      "family": "Poaceae",
      "water_need": "medium",
      "suitable_soils": [
        "loamy",
        "clay"
      ],
      "temperature_range_c": {
        "min": 5,
        "max": 25
      },
      "annual_precipitation_range_mm": {
        "min": 350,
        "max": 750
      }
    }
  ]
}
```

### Zorunlu ürün alanları

| Alan | Tip | Açıklama |
|---|---|---|
| `id` | string | Ürünün kod içinde kullanılan benzersiz kimliği |
| `name` | string | Kullanıcıya gösterilecek ürün adı |
| `family` | string | Bitkinin botanik ailesi |
| `water_need` | string | `low`, `medium` veya `high` |
| `suitable_soils` | string listesi | Ürüne uygun toprak türleri |
| `temperature_range_c` | object | Önerilen minimum ve maksimum sıcaklık |
| `annual_precipitation_range_mm` | object | Önerilen yıllık yağış aralığı |

`backend/data/crops.json` dosyasının kök yapısı doğrudan bir JSON listesi olacaktır. `/api/crops` endpoint’i bu listeyi `crops` alanı içinde döndürecektir.

---

## 6. Analiz İsteği

### İstek

```http
POST /api/analyze
Content-Type: application/json
```

### İstek gövdesi

```json
{
  "latitude": 37.8746,
  "longitude": 32.4932,
  "start_date": "2025-11-08",
  "end_date": "2026-11-07",
  "current_crop": "wheat",
  "soil_type": "loamy",
  "priority": "water_saving"
}
```

### Alan kuralları

| Alan | Tip | Kural |
|---|---|---|
| `latitude` | number | `-90` ile `90` arasında olmalı |
| `longitude` | number | `-180` ile `180` arasında olmalı |
| `start_date` | string | `YYYY-MM-DD` formatında olmalı |
| `end_date` | string | `YYYY-MM-DD` formatında olmalı |
| `current_crop` | string | `crops.json` içindeki ürün kimliklerinden biri olmalı |
| `soil_type` | string | `sandy`, `loamy`, `clay` veya `silty` |
| `priority` | string | `balanced`, `water_saving` veya `yield` |

`start_date`, `end_date` tarihinden sonra olamaz.

Frontend tarihleri `YYYY-MM-DD` biçiminde gönderir. NASA servisi bu tarihleri NASA POWER isteğinde kullanılmak üzere `YYYYMMDD` biçimine dönüştürür.

---

## 7. Analiz Cevabı

### Başarılı cevap

```json
{
  "location": {
    "latitude": 37.8746,
    "longitude": 32.4932,
    "label": "Konya, Türkiye"
  },
  "source": {
    "name": "NASA POWER",
    "mode": "live",
    "time_standard": "LST",
    "start_date": "2025-11-08",
    "end_date": "2026-11-07"
  },
  "summary": {
    "average_temperature_c": 15.8,
    "minimum_temperature_c": -4.2,
    "maximum_temperature_c": 38.1,
    "total_precipitation_mm": 326.4,
    "dry_days": 214,
    "longest_dry_spell_days": 24,
    "hot_days": 17,
    "data_completeness_percent": 98.9
  },
  "risk": {
    "level": "medium",
    "score": 58,
    "reasons": [
      "Uzun kurak dönem tespit edildi.",
      "Toplam yağış miktarı seçilen dönem için düşüktür."
    ]
  },
  "monthly_climate": [
    {
      "month": "2026-01",
      "average_temperature_c": 2.4,
      "precipitation_mm": 31.6
    }
  ],
  "recommendations": [
    {
      "rank": 1,
      "crop_id": "chickpea",
      "crop_name": "Nohut",
      "rotation": [
        "wheat",
        "chickpea"
      ],
      "scores": {
        "total": 84,
        "climate": 82,
        "water": 91,
        "soil": 78,
        "rotation": 86
      },
      "advantages": [
        "Buğdaydan sonra farklı bir bitki ailesi kullanır.",
        "Su ihtiyacı görece düşüktür.",
        "Seçilen toprak türüyle uyumludur."
      ],
      "risks": [
        "Aşırı sıcak dönemlerde verim kaybı oluşabilir."
      ]
    }
  ]
}
```

---

## 8. Kaynak Modları

`source.mode` aşağıdaki değerlerden birini alır:

| Değer | Açıklama |
|---|---|
| `live` | Veri doğrudan NASA POWER API üzerinden alınmıştır |
| `cache` | Daha önce alınmış ve önbelleğe kaydedilmiş veri kullanılmıştır |
| `demo` | NASA servisine ulaşılamadığı için demo verisi kullanılmıştır |

Frontend kullanılan kaynak modunu kullanıcıya göstermelidir. Demo veri kullanılmışsa sonuç gerçek zamanlı NASA verisi gibi sunulmamalıdır.

---

## 9. Normalize Edilmiş İklim Kaydı

NASA POWER cevabı analiz modülüne gönderilmeden önce aşağıdaki ortak yapıya dönüştürülür:

```json
{
  "date": "2026-01-01",
  "temperature_c": 7.4,
  "temperature_min_c": 1.2,
  "temperature_max_c": 13.8,
  "precipitation_mm": 0.6,
  "relative_humidity_percent": 68.4,
  "root_zone_wetness": 0.57
}
```

Her gün için bir kayıt bulunur.

Eksik bir NASA değeri varsa `-999` gibi NASA dolgu değerleri kullanılmamalı, değer `null` yapılmalıdır.

Örnek:

```json
{
  "date": "2026-01-02",
  "temperature_c": null,
  "temperature_min_c": null,
  "temperature_max_c": null,
  "precipitation_mm": 2.1,
  "relative_humidity_percent": null,
  "root_zone_wetness": null
}
```

`RH2M` ve `GWETROOT` zenginleştirici parametrelerdir. Bu iki parametreden biri
veya her ikisi bazı günlerde eksik olduğunda ilgili alan `null` yapılır; temel
sıcaklık ve yağış analizi çalışmaya devam eder. `0` değeri otomatik olarak eksik
sayılmaz. `T2M`, `T2M_MIN`, `T2M_MAX` ve `PRECTOTCORR` temel analiz
parametreleridir.

`backend/data/demo_climate.json` dosyası da aynı kayıt yapısını kullanmalıdır.

---

## 10. NASA POWER İsteği

Kullanılacak servis:

```text
https://power.larc.nasa.gov/api/temporal/daily/point
```

Kullanılacak temel parametreler:

```text
community=AG
parameters=T2M,T2M_MIN,T2M_MAX,PRECTOTCORR,RH2M,GWETROOT
format=JSON
time-standard=LST
```

Parametrelerin anlamları:

| Parametre | Açıklama |
|---|---|
| `T2M` | İki metre yükseklikteki ortalama sıcaklık |
| `T2M_MIN` | Günlük minimum sıcaklık |
| `T2M_MAX` | Günlük maksimum sıcaklık |
| `PRECTOTCORR` | Düzeltilmiş günlük toplam yağış |
| `RH2M` | İki metre yükseklikteki bağıl nem |
| `GWETROOT` | Kök bölgesi toprak ıslaklığı |

NASA API’ye frontend doğrudan istek göndermeyecektir. NASA isteğini yalnızca backend gerçekleştirecektir.

---

## 11. Prototip İklim Kuralları

Hackathon prototipinde aşağıdaki başlangıç kuralları kullanılacaktır:

- Günlük yağış `1 mm` değerinden düşükse gün, kurak gün olarak sayılır.
- Günlük maksimum sıcaklık `35 °C` veya üzerindeyse gün, sıcak gün olarak sayılır.
- Risk skoru `0–33` arasındaysa risk seviyesi `low` olur.
- Risk skoru `34–66` arasındaysa risk seviyesi `medium` olur.
- Risk skoru `67–100` arasındaysa risk seviyesi `high` olur.

Bu eşikler prototip varsayımlarıdır. Kullanıcıya bilimsel olarak kesin tarımsal tavsiyeler gibi sunulmamalıdır.

---

## 12. Hata Cevapları

Kontrollü backend hataları mümkün olduğunca aşağıdaki formatta dönmelidir:

```json
{
  "detail": {
    "code": "NASA_API_UNAVAILABLE",
    "message": "NASA POWER verisine şu anda ulaşılamıyor."
  }
}
```

Kullanılabilecek hata kodları:

| HTTP kodu | Uygulama kodu | Açıklama |
|---|---|---|
| `400` | `INVALID_REQUEST` | İstek mantıksal olarak geçersiz |
| `404` | `CROP_NOT_FOUND` | İstenen ürün bulunamadı |
| `422` | `VALIDATION_ERROR` | Alan tipi veya değeri geçersiz |
| `502` | `NASA_API_UNAVAILABLE` | NASA POWER servisine ulaşılamadı |
| `500` | `INTERNAL_ERROR` | Beklenmeyen backend hatası |

Frontend kullanıcıya ham hata nesnesi veya teknik hata yığını göstermemelidir.

---

## 13. Modüllerin Sorumlulukları

### Frontend

- Kullanıcıdan konum ve tarımsal tercihleri alır.
- `POST /api/analyze` isteğini gönderir.
- Harita, özet kartları, grafikler, riskler ve önerileri gösterir.
- NASA API’ye doğrudan bağlanmaz.

### NASA veri servisi

- NASA POWER API isteğini gerçekleştirir.
- NASA cevabını normalize edilmiş günlük kayıtlara dönüştürür.
- Eksik değerleri temizler.
- Gerektiğinde cache veya demo verisine geçer.

### İklim analizi

- Normalize edilmiş günlük kayıtları kullanır.
- İklim özetini hesaplar.
- Kurak günleri, sıcak günleri ve en uzun kurak dönemi bulur.
- Risk skorunu ve risk nedenlerini üretir.
- Aylık grafik verisini oluşturur.

### Ürün rotasyonu

- Kullanıcının mevcut ürününü, toprak türünü ve önceliğini kullanır.
- İklim analizi sonuçlarını değerlendirir.
- Ürün adaylarını puanlar.
- Sıralanmış ve açıklanabilir öneriler üretir.

### Backend ana akışı

- İstek doğrulamasını gerçekleştirir.
- NASA servisini çağırır.
- İklim analizi ve öneri modüllerini çağırır.
- Sonuçları bu dosyada belirtilen API cevabında birleştirir.

---

## 14. Dosya Sahipliği

| Alan | Sorumlu dal |
|---|---|
| `frontend/` | `frontend` |
| `backend/main.py` | `nasa-data` |
| `backend/models.py` | `nasa-data` |
| `backend/nasa_service.py` | `nasa-data` |
| `backend/data/demo_climate.json` | `nasa-data` |
| `backend/climate_analysis.py` | `climate-analysis` |
| `backend/recommendation.py` | `rotation-engine` |
| `backend/data/crops.json` | `rotation-engine` |
| İlgili test dosyaları | İlgili modülün sorumlu dalı |

Ortak dosyalar ekip koordinasyonu olmadan değiştirilmemelidir.

---

## 15. Sözleşme Değişikliği

Bu dosyada belirtilen alan adları veya veri yapıları geliştirmenin ortasında tek taraflı olarak değiştirilmemelidir.

Değişiklik gerekirse:

1. Ekip üyeleri bilgilendirilir.
2. Frontend ve backend üzerindeki etkisi değerlendirilir.
3. `CONTRACTS.md` güncellenir.
4. Etkilenen modüller aynı sözleşmeye göre güncellenir.
5. Değişiklik pull request açıklamasında belirtilir.
