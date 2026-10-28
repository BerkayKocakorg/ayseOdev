import 'dart:convert';
import 'dart:io' show Platform;
import 'package:crypto/crypto.dart';
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:path/path.dart' as p;
import 'package:shared_preferences/shared_preferences.dart';
import 'package:sqflite/sqflite.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import '../models/user_model.dart';

/// [DatabaseHelper] sınıfı, uygulamanın yerel veritabanı (SQLite) işlemlerini yöneten
/// tekil (Singleton) servis sınıfıdır.
///
/// Sağladığı Yetenekler:
/// 1. Kullanıcı şifrelerini SHA-256 algoritmasıyla tek yönlü özetleme (hashing).
/// 2. Windows, macOS, Linux masaüstü ortamlarında `sqflite_common_ffi` ile SQLite entegrasyonu.
/// 3. Mobil ortamlarda (Android/iOS) yerel SQLite motoru kullanımı.
/// 4. Web tarayıcısı ortamında (`kIsWeb`) SQLite Web FFI eksikliğine karşı otomatik kalıcı depolama yedeği.
/// 5. Kayıt oluşturma (Register), Giriş doğrulama (Login) ve Kullanıcı listeleme işlevleri.
class DatabaseHelper {
  /// Singleton tasarım kalıbı: Tüm uygulama boyunca tek bir veritabanı nesnesi kullanılır.
  static final DatabaseHelper instance = DatabaseHelper._init();
  static Database? _database;

  /// Web ortamında çalışırken yerel kullanıcı listesini saklamak için SharedPreferences anahtarı
  static const String _webUsersKey = 'web_registered_users';

  /// Gizli kurucu metot (Private Constructor)
  DatabaseHelper._init();

  /// Verilen şifre metnini SHA-256 standardı ile hash'ler.
  ///
  /// Örneğin "Gizli123" girildiğinde 64 karakter uzunluğunda benzersiz bir hex dizisi üretilir.
  /// Böylece veritabanı dosyası dışarıdan açılsa bile şifreler asla düz metin olarak okunamaz.
  static String hashPassword(String password) {
    final bytes = utf8.encode(password);
    final digest = sha256.convert(bytes);
    return digest.toString();
  }

  /// Aktif veritabanı bağlantısını getirir, henüz başlatılmamışsa ilklendirir.
  Future<Database?> get database async {
    // Web ortamında yerel C SQLite motoru bulunmadığından null döner, web fallback devreye girer
    if (kIsWeb) {
      return null;
    }

    if (_database != null) return _database!;

    // Windows veya Linux masaüstünde FFI (Foreign Function Interface) kütüphanesini ilklendir
    if (Platform.isWindows || Platform.isLinux) {
      sqfliteFfiInit();
      databaseFactory = databaseFactoryFfi;
    }

    // Veritabanı dosyasını disk üzerinde oluştur/aç
    _database = await _initDB('app_users.db');
    return _database;
  }

  /// Veritabanı dosya yolunu belirler ve SQLite bağlantısını açar
  Future<Database> _initDB(String filePath) async {
    final dbPath = await getDatabasesPath();
    final path = p.join(dbPath, filePath);

    return await openDatabase(
      path,
      version: 1,
      onCreate: _createDB,
    );
  }

  /// Veritabanı ilk kez oluşturulurken çalışan tablo oluşturma fonksiyonu
  Future<void> _createDB(Database db, int version) async {
    // 'users' tablosunu oluşturuyoruz:
    // - id: Otomatik artan birincil anahtar (PRIMARY KEY AUTOINCREMENT)
    // - name: Kullanıcının adı soyadı (NOT NULL)
    // - email: Benzersiz e-posta adresi (NOT NULL UNIQUE)
    // - passwordHash: SHA-256 ile özetlenmiş şifre (NOT NULL)
    // - createdAt: Kayıt oluşturulma zamanı (NOT NULL)
    await db.execute('''
      CREATE TABLE users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        passwordHash TEXT NOT NULL,
        createdAt TEXT NOT NULL
      )
    ''');
  }

  // ==================== KULLANICI İŞLEMLERİ (CRUD) ====================

  /// Verilen e-posta adresinin veritabanında daha önce kayıt edilip edilmediğini denetler.
  /// Büyük/küçük harf duyarsız (Case-insensitive) kontrol yapar.
  Future<bool> checkEmailExists(String email) async {
    final cleanEmail = email.trim().toLowerCase();

    // Web ortamı kontrolü
    if (kIsWeb) {
      final users = await _getWebUsers();
      return users.any((u) => u.email.toLowerCase() == cleanEmail);
    }

    // SQLite veritabanı kontrolü
    final db = await database;
    if (db == null) return false;

    final result = await db.query(
      'users',
      where: 'LOWER(email) = ?',
      whereArgs: [cleanEmail],
      limit: 1,
    );

    return result.isNotEmpty;
  }

  /// Yeni kullanıcı kaydı oluşturur.
  ///
  /// Adımlar:
  /// 1. E-posta adresi sistemde var mı kontrol edilir.
  /// 2. Şifre SHA-256 ile hash'lenir.
  /// 3. Kullanıcı veritabanına eklenir ve oluşturulan nesne geri döndürülür.
  Future<Map<String, dynamic>> registerUser({
    required String name,
    required String email,
    required String password,
  }) async {
    final cleanEmail = email.trim().toLowerCase();

    // 1. E-posta kontrolü
    final exists = await checkEmailExists(cleanEmail);
    if (exists) {
      return {
        'success': false,
        'message': 'Bu e-posta adresi zaten kayıtlı! Lütfen giriş yapın.',
      };
    }

    final now = DateTime.now().toIso8601String();
    final hashedPassword = hashPassword(password);

    final newUser = UserModel(
      name: name.trim(),
      email: cleanEmail,
      passwordHash: hashedPassword,
      createdAt: now,
    );

    try {
      // Web fallback depolaması
      if (kIsWeb) {
        final users = await _getWebUsers();
        final newId = users.isEmpty ? 1 : (users.map((e) => e.id ?? 0).reduce((a, b) => a > b ? a : b) + 1);
        final userWithId = UserModel(
          id: newId,
          name: newUser.name,
          email: newUser.email,
          passwordHash: newUser.passwordHash,
          createdAt: newUser.createdAt,
        );
        users.add(userWithId);
        await _saveWebUsers(users);
        return {
          'success': true,
          'message': 'Kayıt başarıyla oluşturuldu!',
          'user': userWithId,
        };
      }

      // SQLite masaüstü / mobil depolaması
      final db = await database;
      if (db == null) {
        return {
          'success': false,
          'message': 'Veritabanı bağlantısı sağlanamadı.',
        };
      }

      final id = await db.insert(
        'users',
        newUser.toMap(),
        conflictAlgorithm: ConflictAlgorithm.fail,
      );

      final userWithId = UserModel(
        id: id,
        name: newUser.name,
        email: newUser.email,
        passwordHash: newUser.passwordHash,
        createdAt: newUser.createdAt,
      );

      return {
        'success': true,
        'message': 'Kayıt başarıyla oluşturuldu!',
        'user': userWithId,
      };
    } catch (e) {
      return {
        'success': false,
        'message': 'Kayıt sırasında bir hata oluştu: $e',
      };
    }
  }

  /// Kullanıcı girişi kontrolü (Login Authentication).
  ///
  /// Adımlar:
  /// 1. E-posta adresine ait kayıt aranır.
  /// 2. Girilen şifrenin SHA-256 hash'i ile kayıtlı hash karşılaştırılır.
  /// 3. Eşleşme başarılıysa kullanıcı modeli ile birlikte `success: true` döner.
  Future<Map<String, dynamic>> loginUser({
    required String email,
    required String password,
  }) async {
    final cleanEmail = email.trim().toLowerCase();
    final inputHash = hashPassword(password);

    // Web ortamı kontrolü
    if (kIsWeb) {
      final users = await _getWebUsers();
      final userIndex = users.indexWhere((u) => u.email.toLowerCase() == cleanEmail);
      if (userIndex == -1) {
        return {
          'success': false,
          'message': 'Bu e-posta adresine ait kayıtlı kullanıcı bulunamadı.',
        };
      }

      final user = users[userIndex];
      if (user.passwordHash == inputHash) {
        return {
          'success': true,
          'message': 'Giriş başarılı!',
          'user': user,
        };
      } else {
        return {
          'success': false,
          'message': 'Girdiğiniz şifre hatalı. Lütfen kontrol edin.',
        };
      }
    }

    // SQLite kontrolü
    final db = await database;
    if (db == null) {
      return {
        'success': false,
        'message': 'Veritabanına erişilemedi.',
      };
    }

    final result = await db.query(
      'users',
      where: 'LOWER(email) = ?',
      whereArgs: [cleanEmail],
      limit: 1,
    );

    if (result.isEmpty) {
      return {
        'success': false,
        'message': 'Bu e-posta adresine ait kayıtlı kullanıcı bulunamadı.',
      };
    }

    final user = UserModel.fromMap(result.first);
    if (user.passwordHash == inputHash) {
      return {
        'success': true,
        'message': 'Giriş başarılı!',
        'user': user,
      };
    } else {
      return {
        'success': false,
        'message': 'Girdiğiniz şifre hatalı. Lütfen kontrol edin.',
      };
    }
  }

  /// Kullanıcının şifresini sıfırlar / yeniler (Şifremi Unuttum).
  ///
  /// Adımlar:
  /// 1. E-posta adresinin sistemde kayıtlı olup olmadığını denetler.
  /// 2. Yeni şifreyi SHA-256 standardı ile hash'ler.
  /// 3. Veritabanındaki `passwordHash` alanını günceller.
  /// 4. Başarılı ise sonuç haritasında `success: true` döner.
  Future<Map<String, dynamic>> resetPassword({
    required String email,
    required String newPassword,
  }) async {
    final cleanEmail = email.trim().toLowerCase();

    // 1. E-posta sistemde kayıtlı mı?
    final exists = await checkEmailExists(cleanEmail);
    if (!exists) {
      return {
        'success': false,
        'message': 'Bu e-posta adresine kayıtlı bir kullanıcı bulunamadı.',
      };
    }

    final newPasswordHash = hashPassword(newPassword);

    try {
      // Web fallback depolaması
      if (kIsWeb) {
        final users = await _getWebUsers();
        final index = users.indexWhere((u) => u.email.toLowerCase() == cleanEmail);
        if (index == -1) {
          return {
            'success': false,
            'message': 'Bu e-posta adresine kayıtlı bir kullanıcı bulunamadı.',
          };
        }

        final oldUser = users[index];
        users[index] = UserModel(
          id: oldUser.id,
          name: oldUser.name,
          email: oldUser.email,
          passwordHash: newPasswordHash,
          createdAt: oldUser.createdAt,
        );
        await _saveWebUsers(users);

        return {
          'success': true,
          'message': 'Şifreniz başarıyla güncellendi! Yeni şifrenizle giriş yapabilirsiniz.',
        };
      }

      // SQLite masaüstü / mobil depolaması
      final db = await database;
      if (db == null) {
        return {
          'success': false,
          'message': 'Veritabanı bağlantısı sağlanamadı.',
        };
      }

      final count = await db.update(
        'users',
        {'passwordHash': newPasswordHash},
        where: 'LOWER(email) = ?',
        whereArgs: [cleanEmail],
      );

      if (count > 0) {
        return {
          'success': true,
          'message': 'Şifreniz başarıyla güncellendi! Yeni şifrenizle giriş yapabilirsiniz.',
        };
      } else {
        return {
          'success': false,
          'message': 'Şifre güncellenemedi, lütfen tekrar deneyin.',
        };
      }
    } catch (e) {
      return {
        'success': false,
        'message': 'Şifre güncelleme sırasında bir hata oluştu: $e',
      };
    }
  }

  /// Veritabanındaki tüm kayıtlı kullanıcıları listeler.
  /// Ödev sunumunda veritabanı kayıtlarını ekranda göstermek için kullanılır.
  Future<List<UserModel>> getAllUsers() async {
    if (kIsWeb) {
      return await _getWebUsers();
    }

    final db = await database;
    if (db == null) return [];

    final result = await db.query('users', orderBy: 'id DESC');
    return result.map((map) => UserModel.fromMap(map)).toList();
  }

  /// Veritabanında kayıtlı toplam kullanıcı adedini döndürür.
  Future<int> getUserCount() async {
    if (kIsWeb) {
      final users = await _getWebUsers();
      return users.length;
    }

    final db = await database;
    if (db == null) return 0;

    final count = Sqflite.firstIntValue(
      await db.rawQuery('SELECT COUNT(*) FROM users'),
    );
    return count ?? 0;
  }

  // ==================== WEB FALLBACK METOTLARI ====================
  /// Web tarayıcısında çalışırken SharedPreferences üzerindeki JSON listesini çözer
  Future<List<UserModel>> _getWebUsers() async {
    final prefs = await SharedPreferences.getInstance();
    final jsonString = prefs.getString(_webUsersKey);
    if (jsonString == null || jsonString.isEmpty) return [];

    try {
      final List<dynamic> decoded = jsonDecode(jsonString);
      return decoded.map((item) => UserModel.fromMap(Map<String, dynamic>.from(item))).toList();
    } catch (_) {
      return [];
    }
  }

  /// Web ortamındaki güncel kullanıcı listesini JSON string formatında SharedPreferences'a yazar
  Future<void> _saveWebUsers(List<UserModel> users) async {
    final prefs = await SharedPreferences.getInstance();
    final list = users.map((u) => u.toMap()).toList();
    await prefs.setString(_webUsersKey, jsonEncode(list));
  }
}
