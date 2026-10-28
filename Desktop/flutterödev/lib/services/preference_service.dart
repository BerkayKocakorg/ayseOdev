import 'package:shared_preferences/shared_preferences.dart';

/// [PreferenceService], uygulamanın yerel depolama alanı (SharedPreferences) ile
/// iletişim kurmasını sağlayan yardımcı servis sınıfıdır.
///
/// Görevleri:
/// 1. "Beni Hatırla" (Remember Me) onay kutusunun durumunu ve kaydedilen bilgileri saklamak/okumak.
/// 2. Giriş yapmış kullanıcının aktif oturum bilgilerini tutmak.
/// 3. Oturum kapatıldığında gerekli temizlik işlemlerini yapmak.
class PreferenceService {
  // Depolama anahtarları (SharedPreferences Keys)
  static const String _keyRememberMe = 'remember_me';
  static const String _keySavedEmail = 'saved_email';
  static const String _keySavedPassword = 'saved_password';
  static const String _keyCurrentUserName = 'current_user_name';
  static const String _keyCurrentUserEmail = 'current_user_email';

  /// "Beni Hatırla" tercihini ve kullanıcının bilgilerini kaydeder.
  ///
  /// - [remember]: Kullanıcı kutucuğu işaretlediyse `true`, işaretlemediyse `false`.
  /// - [email]: Hatırlanacak e-posta adresi.
  /// - [password]: Opsiyonel olarak hatırlanacak şifre.
  ///
  /// Eğer [remember] `false` ise cihazda önceden saklanan e-posta ve şifre silinir.
  static Future<void> saveRememberMe({
    required bool remember,
    required String email,
    String? password,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    // Kutucuğun durumunu kaydet (true/false)
    await prefs.setBool(_keyRememberMe, remember);

    if (remember) {
      // Beni hatırla aktifse bilgileri kaydet
      await prefs.setString(_keySavedEmail, email);
      if (password != null && password.isNotEmpty) {
        await prefs.setString(_keySavedPassword, password);
      }
    } else {
      // Beni hatırla pasif yapıldıysa eski kayıtları temizle
      await prefs.remove(_keySavedEmail);
      await prefs.remove(_keySavedPassword);
    }
  }

  /// "Beni Hatırla" özelliğinin daha önce aktif edilip edilmediğini döndürür.
  /// Kayıt yoksa varsayılan olarak `false` döner.
  static Future<bool> isRememberMeEnabled() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getBool(_keyRememberMe) ?? false;
  }

  /// Daha önce "Beni Hatırla" ile kaydedilmiş olan e-posta adresini getirir.
  static Future<String?> getSavedEmail() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keySavedEmail);
  }

  /// Daha önce kaydedilmiş olan şifreyi getirir (varsa).
  static Future<String?> getSavedPassword() async {
    final prefs = await SharedPreferences.getInstance();
    return prefs.getString(_keySavedPassword);
  }

  /// Eğer "Beni Hatırla" ile bu e-posta adresi saklanmışsa, yeni şifreyi de günceller.
  static Future<void> updateSavedPasswordIfMatches(String email, String newPassword) async {
    final prefs = await SharedPreferences.getInstance();
    final savedEmail = prefs.getString(_keySavedEmail);
    if (savedEmail != null && savedEmail.trim().toLowerCase() == email.trim().toLowerCase()) {
      await prefs.setString(_keySavedPassword, newPassword);
    }
  }

  /// Giriş yapan kullanıcının bilgilerini aktif oturum olarak kaydeder.
  static Future<void> saveCurrentSession({
    required String name,
    required String email,
  }) async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.setString(_keyCurrentUserName, name);
    await prefs.setString(_keyCurrentUserEmail, email);
  }

  /// Aktif oturumu olan kullanıcının bilgilerini Map olarak döndürür.
  static Future<Map<String, String?>> getCurrentSession() async {
    final prefs = await SharedPreferences.getInstance();
    return {
      'name': prefs.getString(_keyCurrentUserName),
      'email': prefs.getString(_keyCurrentUserEmail),
    };
  }

  /// Kullanıcı oturumu kapattığında (Logout) aktif oturum verilerini siler.
  /// Not: "Beni Hatırla" kayıtlı e-postası korunur, sadece oturum bilgisi düşer.
  static Future<void> clearSession() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.remove(_keyCurrentUserName);
    await prefs.remove(_keyCurrentUserEmail);
  }

  /// Test veya sıfırlama amaçlı tüm SharedPreferences verilerini temizler.
  static Future<void> clearAll() async {
    final prefs = await SharedPreferences.getInstance();
    await prefs.clear();
  }
}
