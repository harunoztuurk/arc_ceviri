# arc - Gerçek Zamanlı Oyun Ekran Çevirmeni & Dil Öğrenim Asistanı 🎮🌐

**arc**, oyun oynarken veya video izlerken ekrandaki İngilizce altyazı ve metinleri **gerçek zamanlı (real-time / 100ms)** olarak algılayan, yapay zeka ile Türkçe'ye çeviren ve ekranın en alt ortasına sinema altyazısı şeklinde şeffaf katman (overlay) olarak yansıtan gelişmiş bir masaüstü uygulamasıdır.

Aynı zamanda çevrilen tüm kelimeleri **tekrarsız (duplicate-free)** veritabanına kaydederek kelime alıştırması (quiz), sesli okuma (TTS) ve Anki aktarımı sunan tam teşekküllü bir **dil öğrenim platformudur**.

---

## 🚀 Öne Çıkan Özellikler

- 📺 **Sinema Altyazısı Modu & Çoklu Monitör Desteği:** 
  - Çoklu ekran kullansanız dahi çeviriler **seçtiğiniz monitörün en alt ortasında** kusursuz bir film altyazısı olarak görünür. Ekranlar arası kayma veya hizalama sorunu yaşanmaz.
- ⚡ **Ultra Hızlı Reaktiftik (100ms / 10 FPS):**
  - Saniyede 10 kare canlı tarama yapar. Harf veya kelime değiştiği an çeviri 0.1 saniyede ekrana yansır.
- 🔍 **%100 Doğrulukta Kelime Algılama (EasyOCR Optimizasyonu):**
  - Pembe, beyaz, gölgeli, renkli veya küçük altyazı fontlarını tek bir kelime dahi atlamadan yakalar.
- ⚡ **Akıllı Önbellek (In-Memory Cache):**
  - Daha önce ekranda çıkan kelimeleri hafızada tutarak **0.001 ms** içinde anında ekrana yansıtır.
- 👁️ **Şeffaf Saydam Katman (Click-Through Overlay):**
  - Tıklamaları engellemez, oyun içi kontrolünüzü veya mouse hareketlerinizi kısıtlamaz.
- ⌨️ **Global Kısayol Tuşları (Global Hotkeys):**
  - `Ctrl + Shift + S`: Oyundayken pencere değiştirmeden canlı çeviriyi başlatır/durdurur.
  - `Alt + R`: Çevrilecek ekran bölgesini seçer.
  - `Alt + T`: **🖱️ Fare Makro Çeviri Tuşu:** Farenin bulunduğu yerdeki kelimeyi/cümleyi anında okuyup yüzen kartta çevirir.
- 📌 **Metin Sabitleme Desteği (Static Text Lock):**
  - Ekranda geçen metin veya altyazı değişmediği sürece (oyun duraklatıldığında veya okuma yaparken) çevrilen cümle ekranda sabit kalır, kaybolmaz.
- 🧠 **Çift Yapay Zeka Çeviri Motoru (Dual-LLM & Meta NLLB-200):**
  - **1. Katman (Hızlı Çevirici):** Metni ~50ms içinde anında çevirip ekrana basar.
  - **2. Katman (Meta NLLB-200 & Llama-3 Refiner):** Arka planda çeviriyi Türkçe gramerine, deyimlere ve oyun bağlamına göre parlatıp mükemmelleştirir.
  - **Ollama / Jan.ai / LM Studio** yerel yapay zeka sunucularını otomatik algılar. Yerel AI kapalıysa kesintisiz çevrimiçi altyapıyı kullanır.
- 📖 **Oyun Terim Sözlüğü (Glossary System):**
  - *Health Potion*, *XP*, *Vault* gibi oyuna özel terimleri kendi Türkçe karşılıklarınızla eşleyebilirsiniz.
- 🎯 **Kelime Alıştırması & Quiz Modu:**
  - Kaydedilen kelimelerinizden rastgele 4 seçenekli testler oluşturarak kelime bilginizi pekiştirir.
- 🔊 **Metin Seslendirme (TTS) & Anki Export:**
  - Kelimelerin telaffuzunu dinleyebilir ve Anki uygulamasına uyumlu `.csv` dosyası olarak aktarabilirsiniz.
- ⚙️ **Kalıcı Görünüm & Ayarlar:**
  - Font boyutu, kart teması, otomatik gizlenme süresi ve konum modunu özelleştirebilirsiniz (`settings.json`).

---

## 💻 Sıfırdan Adım Adım Kurulum Rehberi

Bilgisayarınızda **Python, kütüphaneler veya yapay zeka modelleri yüklü değilse**, aşağıdaki adımları sırasıyla takip ederek uygulamayı ve Meta NLLB-200 motorunu 2 dakikada hazır hale getirebilirsiniz:

---

### 📋 Yüklenecek Bileşenler ve Kütüphane Listesi

| Bileşen / Paket | İşlevi ve Açıklaması |
|---|---|
| 🐍 **Python 3.10+** | Uygulamanın çalışması için gerekli temel programlama dili ortamı. |
| 🖼️ **PyQt6** | Şeffaf sinema altyazı katmanı (overlay) ve kontrol paneli arayüzü. |
| 🔍 **EasyOCR & OpenCV** | Ekrandaki oyun altyazılarını %100 doğrulukla metne dönüştüren görüntü işleme motoru. |
| ⚡ **MSS & Pynput** | Saniyede 10 FPS ultra hızlı ekran yakalama ve global klavye/fare makro dinleyicisi (`Alt+T`). |
| 🧠 **Transformers, Torch & SentencePiece** | Meta'nın **NLLB-200** yapay zeka modelini bilgisayarınızda çalıştıran derin öğrenme altyapısı. |
| 🔊 **PyTTSx3** | Defterdeki kelimeleri sesli telaffuz eden seslendirici (TTS). |
| 🤖 **Ollama & Llama 3** *(İsteğe Bağlı)* | Yerel yapay zeka sunucusu (Port 11434). |

---

### 1️⃣ Adım 1: Python'u İndirin ve Kurun (Zorunlu)
1. **[python.org/downloads](https://www.python.org/downloads/)** adresine gidin ve en güncel Python sürümünü indirin.
2. İndirdiğiniz `.exe` kurulum dosyasını çalıştırın.
3. ⚠️ **ÇOK ÖNEMLİ:** Kurulum penceresinin en altında bulunan **`Add python.exe to PATH`** kutucuğunu **MUTLAKA İŞARETLEYİN!** *(Bu kutucuk işaretlenmezse komut satırı Python'u algılayamaz).*
4. **`Install Now`** butonuna basarak kurulumu tamamlayın.

---

### 2️⃣ Adım 2: Projeyi Bilgisayarınıza İndirin
1. Bu GitHub sayfasındaki yeşil **`Code`** butonuna tıklayın ve **`Download ZIP`** seçeneğini seçin.
2. İnen `.zip` dosyasını bilgisayarınızda istediğiniz bir klasöre çıkartın (örn. Masaüstü).

---

### 3️⃣ Adım 3: Gerekli Tüm Paketleri (Kütüphaneleri) Yükleyin
1. Çıkardığınız **`arc`** klasörünün içine girin.
2. Klasörün üst adres çubuğuna tıklayın, **`cmd`** yazıp **Enter** tuşuna basın *(Klasör konumunda siyah komut penceresi açılacaktır)*.
3. Açılan pencereye aşağıdaki komutu kopyalayıp yapıştırın ve **Enter**'a basın:
   ```bash
   pip install -r requirements.txt
   ```
   *(Bu komut EasyOCR, PyQt6, Meta NLLB-200 PyTorch ve OpenCV kütüphanelerini otomatik olarak indirecektir. İşlem 1-2 dakika sürebilir).*

---

### 4️⃣ Adım 4: Meta NLLB-200 Çeviri Motorunu Yükleyin ve Test Edin 🧠
Meta'nın **NLLB-200 (facebook/nllb-200-distilled-600M)** yapay zeka çeviri modelini bilgisayarınıza indirip canlı çeviri testini çalıştırmak için komut penceresine şu komutu yazın:

```bash
python run_nllb_local.py
```
*(Bu komut Meta'nın resmi NLLB-200 modelini indirecek ve test cümlelerini kusursuz Türkçe ile ekrana basacaktır).*

---

### 5️⃣ Adım 5: Uygulamayı Çalıştırın 🚀

- **Tek Tıkla Başlatma (Tavsiye Edilen):** Klasör içindeki **`baslat.bat`** dosyasına çift tıklayarak uygulamayı anında başlatabilirsiniz.
- **Terminal İle Başlatma:** Komut penceresine `python main.py` yazıp **Enter**'a basabilirsiniz.

---

## 🎮 Oyun İçi Kullanım İpuçları

1. **Bölge Seçimi (`Alt+R`):** Oyuna girmeden veya girdikten sonra `Alt+R` kısayoluna basarak sadece altyazının geçtiği alanı seçin. Bu işlem çeviri hızını ve OCR başarısını maksimuma çıkarır.
2. **Çeviriyi Başlatma (`Ctrl+Shift+S`):** Kısayol tuşuna basarak çeviriciyi başlatıp durdurabilirsiniz.
3. **Pencereli Tam Ekran Modu:** Oyunlarınızı ekran ayarlarından **Pencereli Tam Ekran (Borderless Windowed)** modunda çalıştırmanız altyazı katmanının sorunsuz görünmesini sağlar.

---

## 🤖 Yerel Yapay Zeka (Lokal AI - Ollama & Llama 3) Kurulum Rehberi

**arc**, ekran çevirilerini internete ihtiyaç duymadan tamamen kendi bilgisayarınızda çalışan yerel yapay zeka modelleri (LLM) ile gerçekleştirebilir. **Ollama** ve **Llama 3 (8B Instruct)** modelinin eksiksiz kurulum adımları aşağıdadır:

---

### 1️⃣ Adım 1: Ollama'yı İndirin ve Kurun
1. **[ollama.com/download](https://ollama.com/download)** adresine gidin.
2. **"Download for Windows"** butonuna tıklayarak `OllamaSetup.exe` dosyasını indirin.
3. İndirilen kurulum dosyasını çalıştırıp **Install** butonuna basarak kurulumu tamamlayın.
4. *(Kurulum bittiğinde Windows sağ alt araç çubuğunda/sistem tepsisinde Ollama simgesi görünecektir).*

---

### 2️⃣ Adım 2: Llama 3 (8B Instruct) Modelini İndirin ve Çalıştırın
1. Bilgisayarınızda **Komut İstemcisi (CMD)** veya **PowerShell** uygulamasını açın.
2. Aşağıdaki komutu yazıp **Enter** tuşuna basın:
   ```bash
   ollama run llama-3-8b-instruct
   ```
   *(Alternatif olarak Llama 3.1 sürümü için: `ollama run llama3.1` kullanabilirsiniz).*
3. Ollama yaklaşık **4.7 GB** boyutundaki yapay zeka modelini otomatik olarak indirmeye başlayacaktır.

---

### 3️⃣ Adım 3: Kurulumun Doğrulanması
- İndirme tamamlandığında terminalde `>>> Send a message (/? for help)` ifadesi görünür. Bu durum modelin sorunsuz kurulduğunu ve çalışmaya hazır olduğunu gösterir.
- Ollama arka planda **`http://localhost:11434`** adresi üzerinden yerel API sunucusu sunmaya başlar.

---

### 4️⃣ Adım 4: arc Uygulaması İle Otomatik Bağlantı
- **arc** uygulamasını başlattığınızda (`baslat.bat` veya `python main.py`), sistem otomatik olarak `http://localhost:11434` portunu sorgular.
- Ollama aktifse çeviriler doğrudan ekran kartınız/işlemciniz üzerinden **Llama 3** ile yapılır.
- *(Yerel AI kapalıysa veya Ollama çalışmıyorsa arc otomatik olarak kesintisiz hızlı çevrimiçi çeviri motoruna geçer).*

---

### 💡 Faydalı Ollama Komutları
- **Kurulu modelleri listeleme:** `ollama list`
- **Model sohbetinden çıkış yapma:** `/bye`
- **Ollama'yı arka planda tekrar başlatma:** Windows Başlat menüsüne `Ollama` yazıp tıklamanız yeterlidir.

---

## 📁 Yayın Klasör Yapısı

```
arc/
├── baslat.bat          # Tek tıkla uygulamayı başlatıcı
├── main.py             # Ana masaüstü giriş noktası
├── config.py           # Varsayılan yapılandırma
├── settings_manager.py # Kalıcı ayarlar & Terim sözlüğü
├── hotkey_manager.py   # Global kısayol dinleyicisi (Ctrl+Shift+S, Alt+R)
├── requirements.txt    # Gerekli Python paketleri
├── capture/            # Ekran yakalama motoru (MSS & OpenCV)
├── ocr/                # Görsel metin okuma altyapısı (EasyOCR)
├── translator/         # Yapay Zeka çeviri istemcisi ve önbellek
├── pipeline/           # Asenkron çok izlekli (Multi-threaded) işleme motoru
├── ui/                 # PyQt6 Saydam Altyazı Katmanı, Bölge Seçici & Kontrol Paneli
├── learning/           # SQLite Kelime Defteri, Quiz ve Anki Export
└── tests/              # Birim ve bileşen testleri
```

---

## 📄 Lisans

Bu proje **MIT Lisansı** ile lisanslanmıştır. Serbestçe kullanılabilir ve dağıtılabilir.
