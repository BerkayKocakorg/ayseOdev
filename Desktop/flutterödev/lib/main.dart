import 'dart:io' show Platform;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';
import 'screens/login_screen.dart';
import 'services/network_service.dart';

/// Uygulamanın ana giriş noktası (Entry Point).
///
/// Burada:
/// 1. [WidgetsFlutterBinding.ensureInitialized] çağrılarak asenkron servislerin ve widget altyapısının hazır olması sağlanır.
/// 2. Windows veya Linux masaüstü ortamında SQLite C kütüphanesi (FFI) devreye alınır.
/// 3. [NetworkService.startMonitoring] ile aktif internet bağlantısı periyodik denetlenmeye başlar.
/// 4. [runApp] ile [MyApp] başlatılır.
void main() async {
  // Flutter motorunun widget bağlayıcısını başlatıyoruz (Asenkron main için zorunludur)
  WidgetsFlutterBinding.ensureInitialized();

  // Windows ve Linux masaüstü ortamlarında yerel SQLite veritabanı motorunu (FFI) ilklendiriyoruz
  if (!kIsWeb && (Platform.isWindows || Platform.isLinux)) {
    sqfliteFfiInit();
    databaseFactory = databaseFactoryFfi;
  }

  // Ağ izleme servisini başlatıyoruz
  NetworkService.startMonitoring();

  // Ana uygulamayı ayağa kaldırıyoruz
  runApp(const MyApp());
}

/// [MyApp] kök widget'ı: Uygulama genelinde geçerli olan temayı (ThemeData),
/// başlığı ve ilk açılacak ekranı ([LoginScreen]) tanımlar.
class MyApp extends StatelessWidget {
  const MyApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Flutter Giriş & Kayıt Sistemi',
      // Sağ üstteki hata ayıklama (Debug) bandını gizliyoruz
      debugShowCheckedModeBanner: false,
      // Modern Koyu (Dark) Tema Yapılandırması
      theme: ThemeData(
        brightness: Brightness.dark,
        scaffoldBackgroundColor: const Color(0xFF0F172A), // Koyu lacivert/slate zemin
        colorScheme: const ColorScheme.dark(
          primary: Color(0xFF6366F1),   // Ana tema rengi (Indigo)
          secondary: Color(0xFF8B5CF6), // İkincil vurgu rengi (Violet)
          surface: Color(0xFF1E293B),   // Kart ve diyalog yüzey rengi
          error: Color(0xFFEF4444),     // Hata durumları için kırmızı renk
        ),
        useMaterial3: true,
      ),
      // Uygulama açılışında gösterilecek ilk ekran: Giriş Ekranı
      home: const LoginScreen(),
    );
  }
}
