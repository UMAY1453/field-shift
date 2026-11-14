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
- NASA POWER günlük iklim verisi
- Sıcaklık ve yağış analizi
- Kurak gün ve sıcak gün hesaplaması
- En uzun kurak dönem tespiti
- Açıklanabilir iklim risk skoru
- Toprak ve iklim uyumuna dayalı ürün rotasyonu önerileri
- Chart.js ile iklim grafikleri
- NASA servisine ulaşılamadığında demo veri desteği
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
- Pandas
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
2. Kullanıcı mevcut ürününü, toprak türünü ve önceliğini belirler.
3. Frontend, `POST /api/analyze` isteğini backend’e gönderir.
4. Backend, NASA POWER üzerinden günlük sıcaklık ve yağış verilerini alır.
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
│   ├── climate_analysis.py
│   ├── recommendation.py
│   ├── data/
│   │   ├── crops.json
│   │   └── demo_climate.json
│   └── cache/
└── tests/
    ├── __init__.py
    ├── test_nasa_service.py
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

Beklenen sürüm:

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

## API Endpoint’leri

| Yöntem | Adres | Açıklama |
|---|---|---|
| `GET` | `/api/health` | Backend sağlık kontrolü |
| `GET` | `/api/crops` | Kullanılabilir ürünleri listeler |
| `POST` | `/api/analyze` | İklim analizi ve rotasyon önerisi üretir |

Ayrıntılı istek ve cevap yapıları için `CONTRACTS.md` dosyasına bakın.

## NASA POWER Parametreleri

Prototip aşağıdaki günlük NASA POWER parametrelerini kullanır:

| Parametre | Açıklama |
|---|---|
| `T2M` | Günlük ortalama sıcaklık |
| `T2M_MIN` | Günlük minimum sıcaklık |
| `T2M_MAX` | Günlük maksimum sıcaklık |
| `PRECTOTCORR` | Düzeltilmiş günlük toplam yağış |

NASA POWER verileri `JSON` formatında alınır.

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

## Lisans

Bu proje Apache License 2.0 kapsamında lisanslanmıştır. Ayrıntılar için `LICENSE` dosyasına bakın.

## Veri Atfı

İklim verileri NASA POWER projesinden alınmaktadır:

```text
NASA Prediction Of Worldwide Energy Resources (POWER)
```