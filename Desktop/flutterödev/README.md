# Flutter Giriş & Kayıt Sistemi (Ödev Projesi)

Bu proje, Flutter ile geliştirilmiş; yerel veritabanı (SQLite), güvenli şifreleme (SHA-256), şifre kriter kontrolleri, **çalışan Şifremi Unuttum (Şifre Sıfırlama) akışı**, **gerçek zamanlı İnternet Bağlantı Kontrolü (Offline Hata Yönetimi)** ve "Beni Hatırla" (Remember Me) özelliklerini barındıran modern bir kimlik doğrulama uygulamasıdır.

---

## 🚀 Temel Özellikler

1. **Giriş Ekranı (Login Screen)**
   - E-posta ve şifre doğrulaması.
   - **İnternet Kontrolü:** İnternet yoksa kullanıcıyı "İnternete bağlı değilsiniz!" diyaloğu ile uyarır ve işlemi durdurur.
   - Şifre gizle / göster (göz ikonu) desteği.
   - **Beni Hatırla (Remember Me):** Seçildiğinde kullanıcının bilgileri `SharedPreferences` üzerinde güvenle saklanır ve sonraki açılışta otomatik doldurulur.
   - **Şifremi Unuttum:** Artık tam işlevsel şifre sıfırlama sayfasına (`ForgotPasswordScreen`) yönlendirir.
   - Kayıt ekranına hızlı geçiş.

2. **Şifremi Unuttum / Şifre Sıfırlama (Forgot Password Screen)**
   - Kayıtlı e-posta adresini doğrulama.
   - **Canlı Şifre Kriter Kontrolü:** Yeni şifrenin kurallara uygunluğunu gerçek zamanlı gösterir.
   - Yeni şifre ve şifre tekrar uyuşma denetimi.
   - **İnternet Kontrolü:** Çevrimdışıyken şifre sıfırlama taleplerini engeller ve hata verir.
   - Şifreyi **SHA-256** ile özetleyerek SQLite / SharedPreferences üzerinde günceller.
   - Başarılı sıfırlamada e-posta adresini otomatik olarak Giriş ekranına aktarır.

3. **İnternet Bağlantı & Çevrimdışı Kontrolü (Offline Detection & Error Handling)**
   - **Anlık & Periyodik Ağ Kontrolü:** `NetworkService` arka planda internet erişimini (`google.com` soket sorgusu) test eder.
   - **"İnternete Bağlanın" Hata Penceresi & Bildirim:** Giriş ekranında, kayıt olmada ve şifre sıfırlama işlemlerinde internet kesintisi tespit edilirse işlem durdurulur ve "İnternete Bağlanın" uyarı diyaloğu ile kayan SnackBar bildirimi gösterilir.
   - **Giriş Ekranında Çevrimdışı Uyarı Kartı & Bandı:** İnternet yokken giriş ekranında kullanıcıyı doğrudan bilgilendiren kırmızı uyarı kartı ve ekran tepesinde uyarı bandı görüntülenir.

4. **Kayıt Ekranı (Register Screen)**
   - Ad Soyad, E-posta, Şifre ve Şifre Tekrar alanları.
   - **İnternet Kontrolü:** Çevrimdışıyken işlem engellenir.
   - **Özel Şifre Kriterleri:**
     - 📌 **En az 6 karakter** uzunluk
     - 📌 **En az bir büyük harf (A-Z)**
     - 📌 **En az bir küçük harf (a-z)**
   - **Canlı Kriter Kontrol Paneli:** Kullanıcı şifreyi yazarken sağlanan kriterler anında yeşil onay ikonuyla güncellenir.
   - Şifre tekrar uyuşma doğrulaması.
   - Var olan e-posta kontrolü (Aynı e-posta ile mükerrer kayıt engeli).

5. **Veritabanı ve Güvenlik (Database & Security)**
   - **SQLite (`sqflite` + `sqflite_common_ffi`):** Kullanıcılar yerel veritabanında saklanır. Windows, Android, iOS, Linux ve Web platformlarında sorunsuz çalışacak şekilde yapılandırılmıştır.
   - **SHA-256 Şifreleme (`crypto`):** Kullanıcı şifreleri veritabanına düz metin olarak değil, geri döndürülemez güvenli SHA-256 hash formatında kaydedilir.

6. **Ana Sayfa (Home / Dashboard)**
   - Giriş yapan kullanıcının ad, e-posta ve hesap ID bilgileri.
   - "Beni Hatırla" özelliğinin o anki durumu (Aktif / Pasif).
   - Canlı ağ durumu rozeti ve offline uyarı bandı.
   - **Kayıtlı Kullanıcıları Listele (Veritabanı Test Penceresi):** Veritabanındaki tüm kayıtları inceleyebileceğiniz açılır modal pencere (Ödev sunumu için idealdir).
   - Oturumu Kapat (Logout) butonu.

---

## 📂 Proje Dizin Yapısı

```
lib/
├── main.dart                                # Uygulama başlangıcı, SQLite FFI ve ağ izleyici
├── models/
│   └── user_model.dart                      # Kullanıcı veri modeli
├── services/
│   ├── database_helper.dart                 # SQLite veritabanı, SHA-256 ve şifre sıfırlama
│   ├── network_service.dart                 # İnternet bağlantı denetimi, simülasyon ve diyaloglar
│   └── preference_service.dart              # SharedPreferences (Beni Hatırla & Oturum)
├── screens/
│   ├── login_screen.dart                    # Giriş yap ekranı
│   ├── register_screen.dart                 # Kayıt ol ekranı
│   ├── forgot_password_screen.dart          # Şifremi unuttum / şifre sıfırlama ekranı
│   └── home_screen.dart                     # Giriş sonrası ana panel
└── widgets/
    ├── custom_text_field.dart               # Modern text field bileşeni
    ├── offline_banner.dart                  # Çevrimdışı uyarı bandı ve durum rozeti
    └── password_requirement_indicator.dart  # Canlı şifre kriter göstergesi
```

---

## 🛠️ Çalıştırma Talimatları

### 1. Bağımlılıkları Yükleme
```bash
flutter pub get
```

### 2. Uygulamayı Başlatma
Windows masaüstünde çalıştırmak için:
```bash
flutter run -d windows
```

Tarayıcıda (Chrome) çalıştırmak için:
```bash
flutter run -d chrome
```

Android cihazda çalıştırmak için:
```bash
flutter run
```

### 3. Testleri Çalıştırma
```bash
flutter test
```

### 4. Kod Analizi (Linter)
```bash
dart analyze
```
