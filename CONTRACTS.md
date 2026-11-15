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
      "name": "Buğday"
    }
  ]
}
```

`GET /api/crops`, frontend'in ürün seçim alanlarında kullanacağı hafif bir listedir. Her ürün için yalnızca
`id` ve `name` döndürür; rotasyon kuralları, bilimsel notlar ve kaynaklar API cevabına eklenmez.

### `/api/crops` cevap alanları

| Alan | Tip | Açıklama |
|---|---|---|
| `id` | string | Ürünün kod içinde kullanılan benzersiz kimliği |
| `name` | string | Kullanıcıya gösterilecek ürün adı |

### `backend/data/crops.json` iç veri şeması

`backend/data/crops.json` dosyasının kök yapısı doğrudan bir JSON listesidir. Rotasyon modülü bu dosyayı
doğrudan okuyarak ayrıntılı ürün verilerini kullanır. Backend ana akışı, `/api/crops` cevabını oluştururken
her nesneden yalnızca `id` ve `name` alanlarını seçer.

Her ürün nesnesinde aşağıdaki alanlar bulunur:

| Alan | Tip | Açıklama |
|---|---|---|
| `id` | string | Ürünün benzersiz ve API genelinde kullanılan kimliği |
| `name` | string | Kullanıcıya gösterilecek Türkçe ürün adı |
| `family` | string | Bitkinin botanik ailesi |
| `is_legume` | boolean | Ürünün baklagil olup olmadığı |
| `growing_season` | string listesi | Ürünün yetiştirildiği dönemler: `spring`, `summer`, `autumn`, `winter` |
| `water_need` | string | `low`, `medium` veya `high` |
| `suitable_soils` | string listesi | Sözleşmedeki standart toprak kodlarından uygun olanlar |
| `soil_notes` | string listesi | Drenaj, göllenme ve toprak yapısıyla ilgili kaynaklı ayrıntılar |
| `temperature_range_c` | object | Genel ekolojik optimum sıcaklığın `min` ve `max` değerleri |
| `absolute_temperature_range_c` | object | Genel ekolojik dış sıcaklık sınırlarının `min` ve `max` değerleri |
| `temperature_notes` | string listesi | Ekim, çimlenme veya gelişim dönemlerine özgü sıcaklık açıklamaları |
| `annual_precipitation_range_mm` | object | Önerilen yıllık yağışın `min` ve `max` değerleri |
| `rotation` | object | Ürün tekrarı, rotasyon örnekleri, ortak hastalık grupları ve açıklamalar |
| `sources` | object listesi | Ürün bilgisinin kaynakları ve her kaynağın desteklediği alanlar |

`temperature_range_c`, iklim uygunluğu puanlanırken kullanılan optimum aralıktır.
`absolute_temperature_range_c`, kısa süreli iklim uçlarının risk olarak açıklanmasına yardım eder; tek başına
kesin ürün eleme ölçütü değildir. Birkaç yıllık dönemin mutlak minimum veya maksimum değeri doğrudan genel
uygunsuzluk kararı üretmez. Mümkün olduğunda yetişme dönemine denk gelen aylık iklim özeti kullanılır.

`rotation` nesnesinin alanları:

| Alan | Tip | Açıklama |
|---|---|---|
| `minimum_return_years` | integer veya null | Kaynakta doğrulanmışsa ürünün aynı tarlaya dönüşü için alt sınır |
| `avoid_continuous_cropping` | boolean | Ürünün arka arkaya yetiştirilmesinden kaçınılması gerekip gerekmediği |
| `example_rotations` | string listelerinin listesi | Kaynaklarda verilen ve desteklenen ürün kimliklerine dönüştürülen örnekler |
| `disease_groups` | string listesi | Ürünler arasında ortak hastalık/konukçu riskini eşleştiren grup kodları |
| `notes` | string listesi | Rotasyonun geçerlilik koşulları ve bilimsel sınırlamaları |

`sources` içindeki her nesne `title`, `url` ve `supports` alanlarını içerir. `supports`, ilgili kaynağın hangi
ürün alanlarını desteklediğini gösterir. Doğrulanamayan sayısal bir değer tahmin edilmez; gerektiğinde `null`
kullanılır ve sınırlama sonuçta açıklanır.

Şu an desteklenen ürün kimlikleri:

- `wheat`
- `barley`
- `corn`
- `chickpea`
- `sunflower`
- `canola`
- `potato`
- `processing_tomato`
- `lentil`

`fallow` bir ürün değildir ve `crops.json` içine eklenmez. Yalnızca `previous_crop` için özel arazi durumu
olarak kullanılabilir.

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
  "latitude": 40.195,
  "longitude": 29.06,
  "start_date": "2021-01-01",
  "end_date": "2025-12-31",
  "previous_crop": "wheat",
  "current_crop": "chickpea",
  "next_crop": "sunflower",
  "soil_type": "loamy",
  "priority": "water_saving"
}
```

### Alan kuralları

| Alan | Tip | Kural |
|---|---|---|
| `latitude` | number | `-90` ile `90` arasında olmalı |
| `longitude` | number | `-180` ile `180` arasında olmalı |
| `start_date` | string, isteğe bağlı | `YYYY-MM-DD` formatında olmalı; gönderilmezse `2021-01-01` kullanılır |
| `end_date` | string, isteğe bağlı | `YYYY-MM-DD` formatında olmalı; gönderilmezse `2025-12-31` kullanılır |
| `previous_crop` | string veya null, isteğe bağlı | `crops.json` içindeki ürün kimliklerinden biri, özel `fallow` değeri veya `null` olmalı; gönderilmezse `null` kullanılır |
| `current_crop` | string | Kullanıcının şimdi ekmek veya dikmek istediği ürünün `crops.json` içindeki kimliği olmalı |
| `next_crop` | string veya null, isteğe bağlı | Kullanıcının daha sonraki dönem için planladığı ürünün `crops.json` içindeki kimliği veya `null` olmalı; gönderilmezse `null` kullanılır |
| `soil_type` | string | `sandy`, `loamy`, `clay` veya `silty` |
| `priority` | string | `balanced`, `water_saving` veya `yield` |

`start_date`, `end_date` tarihinden sonra olamaz.

Frontend tarihleri gönderirse `YYYY-MM-DD` biçimini kullanır. NASA servisi bu tarihleri NASA POWER isteğinde kullanılmak üzere `YYYYMMDD` biçimine dönüştürür. Tarihler gönderilmezse backend son beş tamamlanmış yıllık Bursa referans dönemi olan `2021-01-01`–`2025-12-31` aralığını otomatik kullanır.

`start_date` ve `end_date` ürünlerin ekim veya hasat tarihleri değil, NASA iklim analiz dönemidir.
Bu aralık, seçilen ürünün beş yıl boyunca yetiştirileceği anlamına gelmez. `previous_crop → current_crop → next_crop` alanları kesin ay veya yıl sürelerini değil, birbirini izleyen ekim dönemlerini temsil eder.

`climate_result.summary.total_precipitation_mm`, `start_date` ile `end_date` arasındaki analiz döneminin
toplam yağışıdır. Rotasyon modülü bu değeri `annual_precipitation_range_mm` ile karşılaştırmadan önce analiz
süresini gün cinsinden hesaplar ve yıllık ortalamaya dönüştürür:

```text
analysis_years = period_days / 365.2425
annual_precipitation_mm = total_precipitation_mm / analysis_years
```

Bu nedenle rotasyon modülü toplam yağışı sabit olarak `5` değerine bölmez; analiz dönemi değiştiğinde aynı
hesap çalışmaya devam eder.

Backend ana akışı, Kişi 3'ün ürettiği nesneyi değiştirmeden bir kopyasına aşağıdaki alanı ekler:

```json
"metadata": {
  "start_date": "2021-01-01",
  "end_date": "2025-12-31",
  "period_days": 1826
}
```

`period_days` pozitif bir tam sayı olmalı ve `(end_date - start_date).days + 1` sonucuyla birebir
eşleşmelidir. Rotasyon modülü bu tutarlılığı yeniden doğrular.

`total_precipitation_mm` ve `data_completeness_percent` alanlarında boolean, `NaN`, pozitif sonsuzluk veya
negatif sonsuzluk kabul edilmez. Veri tamlığı `0` ile `100` arasında olmalıdır. Veri tamlığı `%100` değerinden
düşükse algoritma çalışmaya devam eder ve yıllık yağış değerlendirmesinin eksik günlerden etkilenebileceğini
`limitations` içinde belirtir.

Ürün geçmişi ve planı için aşağıdaki kurallar uygulanır:

- `previous_crop: null`, kullanıcının önceki ürünü bilmediği anlamına gelir. Önceki ürüne bağlı rotasyon değerlendirmesi yapılmaz.
- `previous_crop: "fallow"`, tarlanın nadasa bırakıldığı anlamına gelir ve bilinmeyen geçmişten ayrı değerlendirilir. `fallow`, `crops.json` içinde bir ürün kimliği değildir.
- `next_crop: null`, kullanıcının daha sonraki dönem için ürün planlamadığı anlamına gelir. Sonraki ürünle geçiş uyumu değerlendirilmez.
- `current_crop`, `crops.json` içindeki geçerli bir ürün olmak zorundadır; `null` veya `fallow` olamaz.
- `previous_crop` yalnızca `null`, `fallow` veya `crops.json` içindeki geçerli bir ürün olabilir.
- `next_crop` yalnızca `null` veya `crops.json` içindeki geçerli bir ürün olabilir; `fallow` olamaz.
- Ürün kimliklerinin birbirine eşit olması istek doğrulama hatası değildir. Aynı ürünün tekrarı rotasyon modülü tarafından risk olarak değerlendirilir.

---

## 7. Analiz Cevabı

### Başarılı cevap

```json
{
  "location": {
    "latitude": 40.195,
    "longitude": 29.06,
    "label": "Bursa, Türkiye"
  },
  "source": {
    "name": "NASA POWER",
    "mode": "live",
    "time_standard": "LST",
    "start_date": "2021-01-01",
    "end_date": "2025-12-31"
  },
  "summary": {
    "average_temperature_c": 14.1,
    "minimum_temperature_c": -16.2,
    "maximum_temperature_c": 41.1,
    "total_precipitation_mm": 3099.6,
    "dry_days": 1347,
    "longest_dry_spell_days": 69,
    "hot_days": 71,
    "data_completeness_percent": 100.0
  },
  "risk": {
    "level": "high",
    "score": 75,
    "reasons": [
      "Geçerli yağış günlerinin %73.8 kadarı kuru gün olarak sınıflandırıldı.",
      "En uzun kuru dönem 69 gün sürdü.",
      "71 sıcak gün tespit edildi."
    ]
  },
  "monthly_climate": [
    {
      "month": "2021-01",
      "average_temperature_c": 4.3,
      "precipitation_mm": 205.8
    }
  ],
  "planned_rotation_assessment": {
    "crop_id": "chickpea",
    "crop_name": "Nohut",
    "rotation": [
      "wheat",
      "chickpea",
      "sunflower"
    ],
    "scores": {
      "total": 76,
      "climate": 80,
      "water": 72,
      "soil": 78,
      "rotation": 73
    },
    "advantages": [
      "Buğdaydan sonra farklı bir bitki ailesi kullanır."
    ],
    "risks": [
      "Seçilen dönemde su stresi riski dikkate alınmalıdır."
    ],
    "limitations": []
  },
  "recommendations": [
    {
      "rank": 1,
      "crop_id": "barley",
      "crop_name": "Arpa",
      "rotation": [
        "wheat",
        "barley",
        "sunflower"
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

`monthly_climate` içindeki `average_temperature_c` ve `precipitation_mm`
alanları `number` veya `null` olabilir. İlgili ayda bir metrik için hiç geçerli
ölçüm yoksa alan `null` olur; geçerli ölçümlerin tamamı gerçek sıfırsa değer
`0.0` olarak korunur. Veri boşluğunu gizlememek için ay listeden çıkarılmaz.

`planned_rotation_assessment`, kullanıcının `current_crop` olarak seçtiği ürünü; biliniyorsa önceki ve sonraki ürünlerle birlikte değerlendirir.

`recommendations`, `current_crop` yerine aynı ekim için kullanılabilecek alternatifleri içerir. Öneriler, kullanıcının seçtiği üründen sonraki sezon için değildir.

Öneri kuralları:

- `current_crop`, `recommendations` listesinde tekrar edilmez.
- En fazla üç öneri döndürülür.
- Uygun alternatif bulunamazsa `recommendations` boş liste olarak döndürülür.
- Alternatif olabilmek için toplam puan en az `50` olmalıdır.
- Alternatifler önce toplam puana göre azalan, eşit puanda `crop_id` değerine göre artan biçimde sıralanır.
- `rank` değerleri `1` ile başlar ve listede kesintisiz ilerler.
- Kullanıcının seçtiği plan riskli olsa bile `planned_rotation_assessment` döndürülür.
- `previous_crop` veya `next_crop` değeri `null` olduğunda bu bilinmeyen değer `rotation` listesine eklenmez ve değerlendirilemeyen konu `limitations` içinde açıklanır.
- `previous_crop` değeri `fallow` olduğunda özel nadas durumu `rotation` listesinde korunabilir ve nadas kuralları uygulanır.
- `minimum_return_years`, yalnızca `previous_crop → current_crop → next_crop` zinciriyle kesin doğrulanamıyorsa
  sonuç ilgili kaynaklı kuralı `limitations` içinde açıklar. Bu sınırlama, arka arkaya aynı ürünün ayrıca risk
  olarak işaretlenmesini engellemez.

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
  "date": "2021-01-01",
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
  "date": "2021-01-02",
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
| `422` | `INVALID_CROP_SELECTION` | Ürün seçimi veya fallow kullanımı geçersiz |
| `422` | `INVALID_RECOMMENDATION_INPUT` | Toprak veya öncelik seçimi geçersiz |
| `422` | `INSUFFICIENT_CLIMATE_DATA` | Analiz için çekirdek iklim verisi yetersiz |
| `502` | `NASA_API_UNAVAILABLE` | NASA POWER servisine ulaşılamadı |
| `500` | `CLIMATE_ANALYSIS_ERROR` | Normalize iklim verisi analiz sözleşmesine uymadı |
| `500` | `INVALID_CLIMATE_RESULT` | Rotasyon modülüne iletilen iklim sonucu geçersiz |
| `500` | `CROP_DATA_ERROR` | Ürün veri dosyası okunamadı veya bozuk |
| `500` | `RECOMMENDATION_ERROR` | Öneri üretiminde beklenmeyen modül hatası oluştu |
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

- `backend/data/crops.json` dosyasındaki ayrıntılı ürün, iklim eşiği, toprak, rotasyon ve kaynak alanlarını doğrudan okur.
- Kullanıcının önceki ürününü, şimdi ekmek istediği ürünü, isteğe bağlı sonraki ürününü, toprak türünü ve önceliğini kullanır.
- İklim analizi sonuçlarını değerlendirir.
- Kullanıcının seçtiği `previous_crop → current_crop → next_crop` planını değerlendirir.
- `current_crop` yerine kullanılabilecek ürün adaylarını puanlar.
- En fazla üç sıralanmış ve açıklanabilir alternatif öneri üretir.
- Kişi 3'ün ürettiği iklim sonucu alanlarını değiştirmez ve ham NASA verisini yeniden analiz etmez.
- Eksik önceki veya sonraki ürün bilgisini hata olarak değerlendirmez; değerlendirilemeyen noktaları açıklar.

Rotasyon modülünün ana giriş noktası aşağıdaki imzayı kullanacaktır:

```python
def recommend_rotations(
    *,
    previous_crop: str | None,
    current_crop: str,
    next_crop: str | None,
    soil_type: str,
    priority: str,
    climate_result: dict,
) -> dict:
    ...
```

Fonksiyon kendisine verilen `climate_result` sözlüğünü değiştirmez. Yalnızca birleşik API cevabına eklenecek
`planned_rotation_assessment` ve `recommendations` alanlarını yeni bir sözlük içinde döndürür. Puanlamada
kullanılan ortalama, minimum ve maksimum sıcaklık alanları da boolean olmayan sonlu sayılar olarak doğrulanır.

Parametreler yalnızca isimleriyle verilmelidir. Rotasyon modülünün hata sınıfları:

| Hata | Anlamı |
|---|---|
| `RecommendationError` | Bütün rotasyon modülü hatalarının temel sınıfı |
| `InvalidRecommendationInputError` | Geçersiz `soil_type`, `priority` veya diğer kullanıcı girdileri |
| `InvalidCropSelectionError` | Bilinmeyen ürün veya yanlış alanda kullanılan `fallow` |
| `InvalidClimateResultError` | Eksik/geçersiz iklim özeti, tarih aralığı veya toplam yağış |
| `CropDataError` | `crops.json` dosyasının okunamaması veya temel yapısının bozuk olması |

`InvalidCropSelectionError`, `InvalidRecommendationInputError` sınıfından; diğer özel hata sınıfları ise
doğrudan `RecommendationError` sınıfından türer. Böylece backend bütün rotasyon hatalarını
`RecommendationError`, bütün kullanıcı girdisi hatalarını ise `InvalidRecommendationInputError` üzerinden
yakalayabilir.

Rotasyon modülü yeni bir harici paket gerektirmez; `json`, `pathlib` ve `datetime` Python standart
kütüphanelerini kullanır.

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
