# Field Shift

NASA POWER iklim verilerini kullanarak çiftçilere ve tarımsal karar vericilere iklim riski analizi ve açıklanabilir ürün rotasyonu önerileri sunan bir karar destek uygulaması.

Bu proje bir hackathon prototipi olarak geliştirilmektedir.

## Projenin Amacı

Field Shift, kullanıcının seçtiği konuma ait sıcaklık ve yağış verilerini NASA POWER üzerinden alır. Bu verileri analiz ederek:

- İklim koşullarını özetler.
- Kurak günleri ve sıcak günleri belirler.
- Kuraklık riskini puanlar.
- Mevcut ürün, toprak türü ve kullanıcı önceliğine göre ürün rotasyonu önerileri üretir.
- Sonuçları harita, grafik, kart ve açıklamalarla kullanıcıya sunar.

Uygulama kesin tarımsal tavsiye vermek yerine veri temelli bir karar desteği sağlamayı amaçlar.

## Temel Özellikler

- Leaflet tabanlı etkileşimli konum seçimi
- NASA POWER günlük sıcaklık, yağış, bağıl nem ve kök bölgesi ıslaklığı verisi
- Sıcaklık, yağış ve veri tamlığı analizi
- Kurak gün ve sıcak gün hesaplaması
- En uzun kurak dönem tespiti
- Açıklanabilir iklim risk skoru
- Toprak ve iklim uyumuna dayalı ürün rotasyonu önerileri
- Chart.js ile iklim grafikleri
- Tekrarlı istekleri azaltan yerel önbellek (cache)
- NASA servisine ulaşılamadığında Bursa 2021–2025 demo veri desteği
- Mobil ve masaüstü uyumlu kullanıcı arayüzü

## Kullanılan Teknolojiler

### Frontend

- HTML5
- CSS3
- JavaScript
- Leaflet
- Chart.js

### Backend

- Python 3.14.8
- FastAPI
- Uvicorn
- HTTPX
- Pydantic

### Test

- Pytest
- Pytest Asyncio

### Veri Kaynağı

- NASA POWER Daily API

## Sistem Mimarisi

```text
Kullanıcı
   |
   v
HTML / CSS / JavaScript
   |
   | JSON API isteği
   v
FastAPI Backend
   |
   +--> NASA POWER veri servisi
   |
   +--> İklim analiz modülü
   |
   +--> Ürün rotasyonu modülü
   |
   v
JSON analiz cevabı
   |
   v
Harita, grafikler, riskler ve öneriler
```

Frontend, NASA POWER servisine doğrudan bağlanmaz. Bütün dış veri istekleri backend tarafından gerçekleştirilir.

## Veri Akışı

1. Kullanıcı haritadan bir konum seçer.
2. Kullanıcı önceki, mevcut ve sonraki ürün planını; toprak türünü ve önceliğini belirler.
3. Frontend, `POST /api/analyze` isteğini backend’e gönderir.
4. Backend, NASA POWER üzerinden altı günlük iklim parametresini alır.
5. NASA cevabı ortak günlük iklim kayıtlarına dönüştürülür.
6. İklim analiz modülü özet ve risk değerlerini hesaplar.
7. Ürün rotasyonu modülü uygun ürünleri puanlar.
8. Backend birleşik sonucu JSON olarak frontend’e döndürür.
9. Frontend sonuçları harita, grafikler ve öneri kartlarıyla gösterir.

## Proje Yapısı

```text
field-shift/
├── README.md
├── CONTRACTS.md
├── CONTRIBUTING.md
├── requirements.txt
├── .python-version
├── .gitignore
├── LICENSE
├── frontend/
│   ├── index.html
│   ├── css/
│   │   ├── variables.css
│   │   ├── style.css
│   │   └── responsive.css
│   ├── js/
│   │   ├── app.js
│   │   ├── api.js
│   │   ├── map.js
│   │   ├── charts.js
│   │   └── ui.js
│   └── assets/
├── backend/
│   ├── __init__.py
│   ├── main.py
│   ├── models.py
│   ├── nasa_service.py
│   ├── climate_pipeline.py
│   ├── climate_analysis.py
│   ├── recommendation.py
│   ├── data/
│   │   ├── crops.json
│   │   └── demo_climate.json
│   └── cache/
└── tests/
    ├── __init__.py
    ├── test_main.py
    ├── test_nasa_service.py
    ├── test_climate_pipeline.py
    ├── test_crops_data.py
    ├── test_climate_analysis.py
    └── test_recommendation.py
```

## Kurulum

### 1. Repoyu klonlayın

```powershell
git clone https://github.com/UMAY1453/field-shift.git
Set-Location "field-shift"
```

### 2. Sanal ortam oluşturun

```powershell
py -m venv .venv
```

### 3. PowerShell için geçici çalıştırma izni verin

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
```

Bu ayar yalnızca açık olan PowerShell oturumu için geçerlidir.

### 4. Sanal ortamı etkinleştirin

```powershell
.\.venv\Scripts\Activate.ps1
```

### 5. Bağımlılıkları kurun

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

### 6. Python sürümünü kontrol edin

```powershell
python --version
```

Projenin geliştirildiği ve test edildiği sürüm:

```text
Python 3.14.8
```

## Uygulamayı Çalıştırma

### Backend

Proje kök dizininde:

```powershell
python -m uvicorn backend.main:app --reload
```

Backend adresi:

```text
http://127.0.0.1:8000
```

FastAPI dokümantasyonu:

```text
http://127.0.0.1:8000/docs
```

### Frontend

İkinci bir terminal açın ve proje kök dizininde çalıştırın:

```powershell
python -m http.server 5500 --directory frontend
```

Frontend adresi:

```text
http://127.0.0.1:5500
```

Backend ve frontend aynı anda çalışmalıdır.

`127.0.0.1` ve `localhost`, uygulamayı çalıştıran bilgisayarı ifade eder. Repoyu
başka bir bilgisayara klonlayan kişi backend ve frontend komutlarını kendi
bilgisayarında çalıştırdığında bu adresler değişmeden kullanılabilir.

## API Endpoint’leri

| Yöntem | Adres | Açıklama |
|---|---|---|
| `GET` | `/api/health` | Backend sağlık kontrolü |
| `GET` | `/api/crops` | Kullanılabilir ürünleri listeler |
| `POST` | `/api/analyze` | İklim analizi ve rotasyon önerisi üretir |

Ayrıntılı istek ve cevap yapıları için `CONTRACTS.md` dosyasına bakın.

### Örnek analiz isteği

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
  "priority": "water_saving",
  "harvest_start_date": "2027-08-15",
  "harvest_end_date": "2027-09-15"
}
```

Normal kullanıcı akışında iklim referans tarihleri gönderilmeyebilir. Backend
otomatik olarak `2021-01-01`–`2025-12-31` iklim referans dönemini kullanır.
Önceki, mevcut ve sonraki ürünlerle planlanan hasat başlangıç ve bitiş tarihleri
zorunludur:

```json
{
  "latitude": 40.195,
  "longitude": 29.06,
  "previous_crop": "wheat",
  "current_crop": "corn",
  "next_crop": "sunflower",
  "soil_type": "loamy",
  "priority": "water_saving",
  "harvest_start_date": "2027-08-15",
  "harvest_end_date": "2027-09-15"
}
```

İklim referans dönemi, ürünün bu süre boyunca kesintisiz yetiştirileceği
anlamına gelmez. `previous_crop`, `current_crop` ve `next_crop` birbirini izleyen
ekim dönemlerini temsil eder. Hasat tarihleri en fazla 120 günlük planlanan
hasat aralığını belirtir. Backend bu aralığı, hazır 2021–2025 günlük verisindeki
aynı tarihsel dönemlerle karşılaştırır; sonuç bir hava tahmini değildir.

`previous_crop` zorunludur ve tarla nadasa bırakıldıysa `"fallow"` olabilir.
`current_crop` ve `next_crop` zorunlu geçerli ürün kimlikleri olmalıdır.

API cevabındaki `source.mode` alanı veri kaynağının durumunu gösterir:

- `live`: Veri NASA POWER servisinden yeni alındı.
- `cache`: Daha önce alınmış geçerli veri önbellekten kullanıldı.
- `demo`: Bursa 2021–2025 için repoyla birlikte sunulan hazır tarihsel veri
  kullanıldı veya NASA servisine ulaşılamadığında Bursa fallback verisi
  devreye girdi.

Bu üç değer de kontrollü ve geçerli çalışma durumlarıdır.

## NASA POWER Parametreleri

Prototip aşağıdaki günlük NASA POWER parametrelerini kullanır:

| Parametre | Açıklama |
|---|---|
| `T2M` | Günlük ortalama sıcaklık |
| `T2M_MIN` | Günlük minimum sıcaklık |
| `T2M_MAX` | Günlük maksimum sıcaklık |
| `PRECTOTCORR` | Düzeltilmiş günlük toplam yağış |
| `RH2M` | İki metre yükseklikteki bağıl nem |
| `GWETROOT` | Kök bölgesi toprak ıslaklığı |

NASA POWER verileri `community=AG`, `format=JSON` ve `time-standard=LST`
ayarlarıyla alınır. `T2M`, `T2M_MIN`, `T2M_MAX` ve `PRECTOTCORR` çekirdek analiz
parametreleridir. `RH2M` ve `GWETROOT` zenginleştirici parametrelerdir; bu iki
alandaki eksik değerler `null` olarak korunur ve temel analiz akışını durdurmaz.
Gerçek `0` değerleri eksik veri olarak değerlendirilmez.

Hackathon demosunun odak konumu Bursa (`40.195`, `29.06`), varsayılan analiz
dönemi ise 1 Ocak 2021–31 Aralık 2025'tir.

## Branch Yapısı

| Branch | Sorumluluk |
|---|---|
| `main` | Birleştirilmiş ve çalışır proje |
| `frontend` | Arayüz, harita ve grafikler |
| `nasa-data` | FastAPI ve NASA POWER entegrasyonu |
| `climate-analysis` | İklim analizi ve risk hesaplaması |
| `rotation-engine` | Ürün verileri ve rotasyon önerileri |

Katkı kuralları için `CONTRIBUTING.md` dosyasına bakın.

## Prototip Sınırlamaları

- Sonuçlar seçilen dönem ve konum için NASA POWER verilerine dayanır.
- Kullanılan risk eşikleri prototip varsayımlarıdır.
- Ürün önerileri profesyonel tarım danışmanlığının yerine geçmez.
- Yerel toprak ölçümleri ve saha gözlemleri prototipe dahil değildir.
- Demo veri kullanıldığında bu durum kullanıcıya açıkça gösterilmelidir.

## Testler

Bütün testleri çalıştırmak için:

```powershell
python -m pytest
```

Ayrıntılı çıktı için:

```powershell
python -m pytest -v
```

## Yayınlama Notu

GitHub kaynak kodunu barındırır; uygulamayı tek başına internette çalıştırmaz.
Yerel geliştirme ve bilgisayardan yapılacak hackathon sunumu için mevcut
`127.0.0.1` adresleri yeterlidir.

Uygulama internete yayınlanacaksa:

1. FastAPI backend bir sunucuya yayınlanır.
2. Frontend tarafındaki `window.FIELD_SHIFT_API_URL` değeri yayınlanan backend
   adresine ayarlanır. Ayarlanmadığında geliştirme varsayılanı
   `http://127.0.0.1:8000` kullanılır.
3. `backend/main.py` içindeki CORS izinlerine yayınlanan frontend adresi eklenir.
4. `/api/health`, `/api/crops` ve `/api/analyze` için canlı ortam testi yapılır.

Deployment adresleri belli olmadan localhost ve CORS değerleri değiştirilmemelidir.

## Lisans

Bu proje Apache License 2.0 kapsamında lisanslanmıştır. Ayrıntılar için `LICENSE` dosyasına bakın.

## Veri Atfı

İklim verileri NASA POWER projesinden alınmaktadır:

```text
NASA Prediction Of Worldwide Energy Resources (POWER)
```
