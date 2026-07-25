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
  - `Ctrl + Shift + S`: Oyundayken pencere değiştirmeden çeviriyi başlatır/durdurur.
  - `Alt + R`: Çevrilecek ekran bölgesini seçer.
- 🧠 **Çift Çeviri Motoru (Lokal AI & Çevrimiçi Fallback):**
  - **Ollama / Jan.ai / LM Studio** yerel yapay zeka sunucularını otomatik algılar. Yerel AI kapalıysa kesintisiz hızlı çevrimiçi çeviri motoruna geçer.
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

Bilgisayarınızda **Python veya gerekli kütüphaneler yüklü değilse**, aşağıdaki adımları sırasıyla takip ederek uygulamayı 2 dakikada hazır hale getirebilirsiniz:

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

### 3️⃣ Adım 3: Gerekli Paketleri (Kütüphaneleri) Yükleyin
1. Çıkardığınız **`arc`** klasörünün içine girin.
2. Klasörün üst adres çubuğuna tıklayın, **`cmd`** yazıp **Enter** tuşuna basın *(Klasör konumunda siyah komut penceresi açılacaktır)*.
3. Açılan pencereye aşağıdaki komutu kopyalayıp yapıştırın ve **Enter**'a basın:
   ```bash
   pip install -r requirements.txt
   ```
   *(Bu komut EasyOCR, PyQt6, OpenCV ve TTS kütüphanelerini otomatik olarak indirecektir. İşlem 1-2 dakika sürebilir).*

---

### 4️⃣ Adım 4: Uygulamayı Çalıştırın 🚀

- **Tek Tıkla Başlatma (Tavsiye Edilen):** Klasör içindeki **`baslat.bat`** dosyasına çift tıklayarak uygulamayı anında başlatabilirsiniz.
- **Terminal İle Başlatma:** Komut penceresine `python main.py` yazıp **Enter**'a basabilirsiniz.

---

## 🎮 Oyun İçi Kullanım İpuçları

1. **Bölge Seçimi (`Alt+R`):** Oyuna girmeden veya girdikten sonra `Alt+R` kısayoluna basarak sadece altyazının geçtiği alanı seçin. Bu işlem çeviri hızını ve OCR başarısını maksimuma çıkarır.
2. **Çeviriyi Başlatma (`Ctrl+Shift+S`):** Kısayol tuşuna basarak çeviriciyi başlatıp durdurabilirsiniz.
3. **Pencereli Tam Ekran Modu:** Oyunlarınızı ekran ayarlarından **Pencereli Tam Ekran (Borderless Windowed)** modunda çalıştırmanız altyazı katmanının sorunsuz görünmesini sağlar.

---

## 🤖 Yerel Yapay Zeka (Lokal AI) Kullanımı (İsteğe Bağlı)

**arc**, bilgisayarınızda çalışan yerel LLM sunucularını otomatik algılar (Port 11434, 1337, 1234).

- **Ollama Kullanıyorsanız:**
  ```bash
  ollama run llama-3-8b-instruct
  ```
- **LM Studio / Jan.ai Kullanıyorsanız:** Local Server seçeneğini aktif etmeniz yeterlidir.

*(Not: Yerel sunucu kapalıysa arc otomatik olarak hızlı çevrimiçi çeviri altyapısını kullanır.)*

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
