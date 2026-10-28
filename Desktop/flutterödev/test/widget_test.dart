import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_odev/main.dart';
import 'package:flutter_odev/models/user_model.dart';
import 'package:flutter_odev/services/database_helper.dart';
import 'package:flutter_odev/services/network_service.dart';
import 'package:flutter_odev/widgets/password_requirement_indicator.dart';

/// Otomatik Birim (Unit) ve Arayüz (Widget) Testleri
/// Bu testler projenin istenen gereksinimleri tam olarak karşıladığını doğrular.
void main() {
  // 1. Grup: Ödevde istenen şifre kurallarının testleri
  group('Şifre Kuralı Doğrulama Testleri', () {
    test('Şifre 6 karakterden az ise geçersiz olmalı', () {
      expect(PasswordRequirementIndicator.isValid('Ab1'), isFalse);
      expect(PasswordRequirementIndicator.isValid('Abcde'), isFalse);
    });

    test('Büyük harf içermeyen şifre geçersiz olmalı', () {
      expect(PasswordRequirementIndicator.isValid('abcdef123'), isFalse);
    });

    test('Küçük harf içermeyen şifre geçersiz olmalı', () {
      expect(PasswordRequirementIndicator.isValid('ABCDEF123'), isFalse);
    });

    test('En az 6 karakter, büyük ve küçük harf içeren şifre geçerli olmalı', () {
      expect(PasswordRequirementIndicator.isValid('Abc1234'), isTrue);
      expect(PasswordRequirementIndicator.isValid('Password'), isTrue);
      expect(PasswordRequirementIndicator.isValid('Deneme1'), isTrue);
    });
  });

  // 2. Grup: SHA-256 şifreleme ve Veri Modeli testleri
  group('Kullanıcı Modeli ve Şifreleme Testleri', () {
    test('SHA-256 şifreleme aynı girdi için tutarlı hash üretmeli', () {
      final hash1 = DatabaseHelper.hashPassword('GizliSifre123');
      final hash2 = DatabaseHelper.hashPassword('GizliSifre123');
      final hashFarkli = DatabaseHelper.hashPassword('BaskaSifre');

      expect(hash1, equals(hash2));
      expect(hash1, isNot(equals(hashFarkli)));
      expect(hash1.length, equals(64)); // SHA-256 çıktısı her zaman 64 karakterdir
    });

    test('UserModel Map dönüşümleri doğru çalışmalı', () {
      final user = UserModel(
        id: 1,
        name: 'Ahmet Yılmaz',
        email: 'ahmet@example.com',
        passwordHash: 'hash123',
        createdAt: '2026-10-25T12:00:00.000',
      );

      final map = user.toMap();
      expect(map['name'], 'Ahmet Yılmaz');
      expect(map['email'], 'ahmet@example.com');

      final reconstructed = UserModel.fromMap(map);
      expect(reconstructed.id, 1);
      expect(reconstructed.name, user.name);
      expect(reconstructed.email, user.email);
    });
  });

  // 3. Grup: Ağ & İnternet Bağlantısı Servis Testleri
  group('Ağ Bağlantısı ve Çevrimdışı Kontrol Testleri', () {
    test('Simülasyon açıkken isConnected false dönmeli', () async {
      NetworkService.toggleSimulation(true);
      final connected = await NetworkService.isConnected();
      expect(connected, isFalse);
      expect(NetworkService.isSimulatedOffline, isTrue);

      // Test bittikten sonra simülasyonu kapat
      NetworkService.toggleSimulation(false);
      expect(NetworkService.isSimulatedOffline, isFalse);
    });
  });

  // 4. Grup: Şifre Sıfırlama (Şifremi Unuttum) Testleri
  group('Şifre Sıfırlama Fonksiyon Testleri', () {
    test('Kayıtlı olmayan e-posta için sıfırlama başarısız olmalı', () async {
      final result = await DatabaseHelper.instance.resetPassword(
        email: 'kayitsiz_kullanici_test@example.com',
        newPassword: 'YeniSifre123',
      );

      expect(result['success'], isFalse);
      expect(result['message'], contains('bulunamadı'));
    });
  });

  // 5. Grup: Arayüz (Widget) testleri
  group('Arayüz Widget Testleri', () {
    testWidgets('Giriş ekranı render edilmeli ve Şifremi Unuttum butonu bulunmalı', (WidgetTester tester) async {
      await tester.pumpWidget(const MyApp());
      await tester.pump();

      expect(find.text('Giriş Yap'), findsWidgets);
      expect(find.text('Beni Hatırla'), findsOneWidget);
      expect(find.text('Hemen Kayıt Ol'), findsOneWidget);
      expect(find.text('Şifremi Unuttum?'), findsOneWidget);
    });

    testWidgets('Şifremi Unuttum butonuna tıklandığında Şifre Sıfırlama Ekranı açılmalı', (WidgetTester tester) async {
      await tester.pumpWidget(const MyApp());
      await tester.pump();

      // Şifremi Unuttum butonuna tıkla
      await tester.tap(find.text('Şifremi Unuttum?'));
      await tester.pumpAndSettle();

      // Şifre sıfırlama sayfasının öğelerini doğrula
      expect(find.text('Yeni Şifre Belirleyin'), findsOneWidget);
      expect(find.text('Şifremi Güncelle'), findsOneWidget);
      expect(find.text('Giriş Ekranına Dön'), findsOneWidget);
    });
  });
}
