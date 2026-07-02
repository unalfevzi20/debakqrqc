# DEBAK QRQC APP (Quick Response Quality Control)

DEBAK QRQC APP, endüstriyel kalite yönetim süreçlerini ve günlük operasyonel toplantıları kolaylaştırmak amacıyla geliştirilmiş, modern ve dinamik bir **Streamlit** uygulamasıdır.

Bu yazılım; günlük toplantıların kaydedilmesini, ortaya çıkan kalitesizlik ve süreç problemlerinin tespit edilmesini, kök neden analizlerinin yapılmasını ve atanan aksiyon kalemlerinin verimli bir şekilde izlenmesini sağlar.

---

## 🚀 Özellikler

Uygulama, dinamik sol menü (sidebar) navigasyonu ile aşağıdaki 5 ana modülü sunar:

1. **📅 Sabah Toplantısı**: Günlük QRQC toplantı oturumlarının başlatılması, katılımcıların girilmesi, toplantı süresinin takibi ve toplantı sırasında karşılaşılan problemlerin (SQCD kategorilerine göre) kaydedilmesi.
2. **📊 Aksiyon Takip Panosu**: Açılan problemlere atanan aksiyonların, sorumluların, termin tarihlerinin ve aksiyon durumlarının izlendiği canlı pano.
3. **🔍 Kök Neden Analizi**: Problemlerin kaynağına inmek için kullanılan **5 Neden (5 Why) Analizi** aracı.
4. **⚠️ Geciken Aksiyonlar**: Belirlenen termin tarihini aşmış ve henüz kapatılmamış aksiyonların hızlı tespiti.
5. **🔴 Açık Problemler**: Çözülmeyi bekleyen aktif sorunların genel listesi.

---

## 🛠️ Teknolojiler

*   **Arayüz**: [Streamlit](https://streamlit.io/) (Python tabanlı hızlı web uygulama kütüphanesi)
*   **Veritabanı**: SQLite (Lokal ve hafif veritabanı çözümü)
*   **ORM**: SQLAlchemy (Python SQL Toolkit ve Nesne İlişkisel Eşleme aracı)
*   **Veri Analizi**: Pandas

---

## 📋 Kurulum ve Çalıştırma

Uygulamayı yerel bilgisayarınızda çalıştırmak için aşağıdaki adımları izleyebilirsiniz.

### 1. Gereksinimleri Yükleme
Öncelikle gerekli kütüphaneleri yükleyin:
```bash
pip install -r requirements.txt
```

### 2. Örnek Veri Yükleme (Opsiyonel)
Sistemde test verileri ile başlamak isterseniz, örnek veritabanını oluşturmak için demo tohumlama betiğini çalıştırabilirsiniz:
```bash
python seed_demo.py
```
*(Bu komut `qrqc.db` dosyasını oluşturur ve içerisine 2 tamamlanmış toplantı ile örnek problemler/aksiyonlar ekler.)*

### 3. Uygulamayı Başlatma
Uygulamayı direkt çalıştırmak için terminalden şu komutu verin:
```bash
streamlit run app.py
```

Alternatif olarak, Windows kullanıcıları proje dizinindeki **`start.bat`** dosyasına çift tıklayarak uygulamayı tek tıkla başlatabilirler.

---

## 📂 Dosya Yapısı

*   `app.py`: Streamlit arayüzünü ve sayfa yönlendirme mantığını barındıran ana uygulama dosyası.
*   `models.py`: SQLAlchemy tabanlı veritabanı şemasını ve tabloları (`meetings`, `issues`, `actions`) tanımlayan dosya.
*   `seed_demo.py`: Veritabanını test verileriyle dolduran betik.
*   `start.bat`: Uygulamayı kolayca başlatmanızı sağlayan toplu iş dosyası.
*   `requirements.txt`: Uygulamanın çalışması için gerekli bağımlılıklar listesi.
*   `logo.png`: Uygulamada kullanılan görsel varlıklar.
*   `.gitignore`: Gereksiz veya geçici dosyaların (örn. `qrqc.db` veritabanı ve Python önbellekleri) git'e gitmesini engelleyen yapılandırma.
