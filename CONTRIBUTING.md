# Field Shift — Katkı Rehberi

## 1. Amaç

Bu belge, Field Shift projesinde kullanılacak Git, branch, commit, pull request ve dosya sahipliği kurallarını tanımlar.

Proje dört kişi tarafından kısa sürede geliştirileceği için herkesin yalnızca kendi sorumluluk alanında çalışması önemlidir.

---

## 2. Branch Yapısı

Projede bir ana branch ve dört çalışma branch’i bulunur:

| Branch | Sorumluluk |
|---|---|
| `main` | Birleştirilmiş ve çalışır durumdaki proje |
| `frontend` | Arayüz, harita, grafikler ve kullanıcı etkileşimleri |
| `nasa-data` | FastAPI, NASA POWER bağlantısı ve veri normalizasyonu |
| `climate-analysis` | İklim özeti ve risk hesaplamaları |
| `rotation-engine` | Ürün verileri ve rotasyon önerileri |

İkinci bir ana branch veya `develop` branch’i kullanılmayacaktır.

---

## 3. Temel Kurallar

- Özellik geliştirmeleri doğrudan `main` branch’inde yapılmaz.
- Her ekip üyesi kendi branch’inde çalışır.
- `main` branch’ine yalnızca pull request üzerinden değişiklik gönderilir.
- Başka bir kişinin sorumlu olduğu dosya izinsiz değiştirilmez.
- API alan adları `CONTRACTS.md` dosyasına uygun olmalıdır.
- Büyük ve ilgisiz değişiklikler aynı commit içine konulmamalıdır.
- `.venv`, cache dosyaları ve kişisel editör ayarları Git’e eklenmemelidir.
- Şifre, erişim anahtarı veya gizli bilgi repoya yazılmamalıdır.
- NASA POWER API için erişim anahtarı gerekmemektedir.

---

## 4. Dosya Sahipliği

### Frontend sorumlusu

Branch:

```text
frontend
```

Dosyalar:

```text
frontend/index.html
frontend/css/variables.css
frontend/css/style.css
frontend/css/responsive.css
frontend/js/app.js
frontend/js/api.js
frontend/js/map.js
frontend/js/charts.js
frontend/js/ui.js
frontend/assets/
```

### NASA veri ve backend sorumlusu

Branch:

```text
nasa-data
```

Dosyalar:

```text
backend/main.py
backend/models.py
backend/nasa_service.py
backend/data/demo_climate.json
tests/test_nasa_service.py
```

### İklim analizi sorumlusu

Branch:

```text
climate-analysis
```

Dosyalar:

```text
backend/climate_analysis.py
tests/test_climate_analysis.py
```

### Ürün rotasyonu sorumlusu

Branch:

```text
rotation-engine
```

Dosyalar:

```text
backend/recommendation.py
backend/data/crops.json
tests/test_recommendation.py
```

### Ortak dosyalar

Aşağıdaki dosyalar ortak dosyalardır ve ekip koordinasyonu olmadan değiştirilmemelidir:

```text
README.md
CONTRACTS.md
CONTRIBUTING.md
requirements.txt
.gitignore
.python-version
LICENSE
backend/__init__.py
tests/__init__.py
```

---

## 5. İlk Kurulum

Repo bilgisayara klonlanır:

```powershell
git clone https://github.com/UMAY1453/field-shift.git
Set-Location "field-shift"
```

Sanal ortam oluşturulur:

```powershell
py -m venv .venv
```

PowerShell geçici çalıştırma izni verilir:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
```

Sanal ortam etkinleştirilir:

```powershell
.\.venv\Scripts\Activate.ps1
```

Bağımlılıklar kurulur:

```powershell
python -m pip install -r requirements.txt
```

Sanal ortamın doğru çalıştığı kontrol edilir:

```powershell
python --version
where.exe python
```

---

## 6. Kendi Branch’ine Geçme

Önce uzak branch bilgileri alınır:

```powershell
git fetch origin
```

Branch bilgisayarda henüz yoksa ilgili komut çalıştırılır.

### Frontend

```powershell
git switch --track origin/frontend
```

### NASA veri ve backend

```powershell
git switch --track origin/nasa-data
```

### İklim analizi

```powershell
git switch --track origin/climate-analysis
```

### Ürün rotasyonu

```powershell
git switch --track origin/rotation-engine
```

Branch daha önce oluşturulmuşsa yalnızca şu komut yeterlidir:

```powershell
git switch BRANCH_ADI
```

Örnek:

```powershell
git switch frontend
```

Aktif branch kontrol edilir:

```powershell
git branch --show-current
```

---

## 7. Çalışmaya Başlamadan Önce

Her çalışma oturumunun başında:

```powershell
git switch KENDI_BRANCH_ADIN
git status
git pull origin KENDI_BRANCH_ADIN
```

`git status` çıktısı kontrol edilmeden pull yapılmamalıdır. Commit edilmemiş değişiklik varsa önce değişiklikler gözden geçirilmelidir.

---

## 8. Değişiklikleri Kontrol Etme

Değiştirilen dosyalar:

```powershell
git status --short
```

Yapılan satır değişiklikleri:

```powershell
git diff
```

Commit’e hazırlanmış değişiklikler:

```powershell
git diff --staged
```

`.venv` klasörü `git status` çıktısında görünmemelidir.

---

## 9. Dosyaları Commit’e Ekleme

Mümkün olduğunca yalnızca değiştirilen ve ilgili dosyalar eklenmelidir.

Örnek:

```powershell
git add frontend/index.html
git add frontend/css/style.css
git add frontend/js/app.js
```

Bütün dosyaları eklemek gerekiyorsa önce `git status` kontrol edilmeli, ardından şu komut kullanılmalıdır:

```powershell
git add .
```

Commit atmadan önce:

```powershell
git status --short
git diff --staged
```

---

## 10. Commit Mesajları

Commit mesajları kısa ve açıklayıcı olmalıdır.

Kullanılabilecek türler:

| Tür | Kullanım |
|---|---|
| `feat` | Yeni özellik |
| `fix` | Hata düzeltmesi |
| `docs` | Belge değişikliği |
| `test` | Test ekleme veya düzeltme |
| `refactor` | Davranışı değiştirmeyen kod düzenlemesi |
| `chore` | Proje yapısı veya araç değişikliği |
| `style` | Görsel veya biçimsel değişiklik |

Örnekler:

```powershell
git commit -m "feat: add interactive location map"
git commit -m "feat: integrate NASA POWER daily data"
git commit -m "feat: calculate drought risk indicators"
git commit -m "feat: add crop rotation scoring"
git commit -m "fix: handle missing precipitation values"
git commit -m "docs: update API contract"
```

`update`, `changes` veya `final` gibi belirsiz commit mesajları kullanılmamalıdır.

---

## 11. Branch’i GitHub’a Gönderme

Commit oluşturulduktan sonra kişinin kendi branch’i gönderilir:

```powershell
git push origin KENDI_BRANCH_ADIN
```

Örnek:

```powershell
git push origin frontend
```

Doğrudan `main` branch’ine push yapılmamalıdır.

---

## 12. Pull Request Açma

GitHub üzerinden kişinin kendi branch’inden `main` branch’ine pull request açılır.

Örnek:

```text
base: main
compare: frontend
```

Pull request açıklamasında şunlar bulunmalıdır:

- Yapılan değişikliklerin özeti
- Değiştirilen ana dosyalar
- Değişikliğin nasıl test edildiği
- Bilinen eksikler veya sorunlar
- Varsa ekran görüntüsü

Örnek açıklama:

```text
## Özet

- Leaflet haritası eklendi.
- Harita tıklamasından enlem ve boylam alınması sağlandı.
- Analiz formu API isteğine bağlandı.

## Test

- Chrome üzerinde test edildi.
- Mobil görünüm kontrol edildi.
- Seçilen koordinatların forma doğru aktarıldığı doğrulandı.

## Bilinen eksikler

- Backend bağlantısı tamamlanana kadar demo cevap kullanılıyor.
```

---

## 13. Pull Request Kontrol Listesi

Pull request açmadan önce:

- [ ] Değişiklikler doğru branch’te yapıldı.
- [ ] Yalnızca sorumluluk alanındaki dosyalar değiştirildi.
- [ ] `git status` kontrol edildi.
- [ ] `.venv` veya cache dosyaları commit’e eklenmedi.
- [ ] Kodda gizli bilgi bulunmuyor.
- [ ] API alanları `CONTRACTS.md` ile uyumlu.
- [ ] İlgili testler çalıştırıldı.
- [ ] Uygulama temel seviyede elle kontrol edildi.
- [ ] Pull request açıklaması yazıldı.

---

## 14. Testleri Çalıştırma

Bütün testler:

```powershell
python -m pytest
```

Belirli bir test dosyası:

```powershell
python -m pytest tests/test_nasa_service.py
```

Ayrıntılı çıktı:

```powershell
python -m pytest -v
```

Bir pull request birleştirilmeden önce ilgili modülün testleri çalıştırılmalıdır.

---

## 15. JSON Dosyalarını Kontrol Etme

Ürün verisini kontrol etmek için:

```powershell
Get-Content "backend\data\crops.json" -Raw | ConvertFrom-Json | Out-Null
```

Demo iklim verisini kontrol etmek için:

```powershell
Get-Content "backend\data\demo_climate.json" -Raw | ConvertFrom-Json | Out-Null
```

Komut hata vermeden tamamlanırsa JSON sözdizimi geçerlidir.

---

## 16. Main Branch’indeki Değişiklikleri Alma

Kişinin çalışma branch’indeyken önce çalışma alanı temiz olmalıdır:

```powershell
git status
```

Ardından güncel `main` bilgisi alınır:

```powershell
git fetch origin
```

`main` değişiklikleri çalışma branch’ine birleştirilir:

```powershell
git merge origin/main
```

Çakışma çıkarsa rastgele çözüm yapılmamalı, ilgili dosyanın sahibiyle iletişim kurulmalıdır.

Hackathon süresince ekip için daha anlaşılır olması amacıyla zorunlu olmadıkça `rebase` kullanılmayacaktır.

---

## 17. Merge Çakışmaları

Çakışma oluşursa:

1. `git status` çalıştırılır.
2. Çakışan dosyalar belirlenir.
3. Dosyanın sorumlusu bilgilendirilir.
4. Doğru içerik birlikte belirlenir.
5. Çakışma işaretleri temizlenir.
6. İlgili dosya yeniden test edilir.
7. Çözüm commit edilir.

Aşağıdaki işaretler dosyada bırakılmamalıdır:

```text
<<<<<<<
=======
>>>>>>>
```

---

## 18. Merge Sırası

Modüllerin önerilen birleştirme sırası:

1. `climate-analysis`
2. `rotation-engine`
3. `nasa-data`
4. `frontend`

Bu sıra zorunlu değildir ancak backend ana akışının hazır analiz ve öneri fonksiyonlarını kullanmasını kolaylaştırır.

Her merge işleminden sonra `main` branch’i test edilmelidir.

---

## 19. Yasaklanan İşlemler

Aşağıdaki işlemler ekip koordinasyonu olmadan yapılmamalıdır:

```text
git push --force
git reset --hard
git clean -fd
git branch -D
```

Ayrıca:

- Başka bir ekip üyesinin branch’i silinmemelidir.
- Çalışan kod açıklama yapılmadan tamamen değiştirilmemelidir.
- Büyük otomatik biçimlendirmeler yapılmamalıdır.
- `LICENSE` dosyası değiştirilmemelidir.
- `.git` ve `.venv` klasörleri elle düzenlenmemelidir.

---

## 20. Hackathon Önceliği

Öncelik sırası:

1. Çalışan uçtan uca demo
2. NASA verisinin kullanılması
3. Anlaşılır sonuç ve öneriler
4. Hata durumunda demo verisine geçiş
5. Temel testler
6. Görsel iyileştirmeler
7. Ek özellikler

Önce temel kullanıcı akışı tamamlanmalı, zaman kalırsa ek özellikler geliştirilmelidir.