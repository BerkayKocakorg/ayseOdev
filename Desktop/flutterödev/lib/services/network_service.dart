import 'dart:async';
import 'dart:io' show InternetAddress, SocketException;
import 'package:flutter/foundation.dart' show kIsWeb;
import 'package:flutter/material.dart';

/// [NetworkService], uygulamanın internet bağlantı durumunu yöneten ve
/// çevrimdışı (offline) kontrolleri sağlayan servis sınıfıdır.
///
/// Yetenekleri:
/// 1. [isConnected]: Gerçek soket/DNS araması (google.com) ile aktif internet erişimini test eder.
/// 2. [isOnlineNotifier]: Ağ durumundaki değişiklikleri gerçek zamanlı olarak arayüze bildirir.
/// 3. [showNoInternetDialog]: İnternet yokken modern ve açıklayıcı bir "İnternete Bağlanın" hata penceresi sunar.
/// 4. [showNoInternetSnackBar]: Kayan kırmızı "Lütfen internete bağlanın" bildirim çubuğu gösterir.
class NetworkService {
  /// Gerçek zamanlı bağlantı durumunu dinleyen ValueNotifier
  static final ValueNotifier<bool> isOnlineNotifier = ValueNotifier<bool>(true);

  // Periyodik bağlantı denetim zamanlayıcısı
  static Timer? _pollingTimer;

  /// Aktif internet bağlantısını denetler.
  ///
  /// - Web ortamında (`kIsWeb`) tarayıcı ortamı kabul edilir.
  /// - Windows, Android, iOS, Linux ortamlarında `InternetAddress.lookup('google.com')`
  ///   çağrısı 2.5 saniyelik zaman aşımı (timeout) ile test edilir.
  static Future<bool> isConnected() async {
    if (kIsWeb) {
      return true;
    }

    try {
      final result = await InternetAddress.lookup('google.com')
          .timeout(const Duration(milliseconds: 2500));
      return result.isNotEmpty && result[0].rawAddress.isNotEmpty;
    } on SocketException catch (_) {
      return false;
    } on TimeoutException catch (_) {
      return false;
    } catch (_) {
      return false;
    }
  }

  /// Anlık bağlantı kontrolü yapar ve [isOnlineNotifier] değerini günceller
  static Future<bool> checkConnection() async {
    final connected = await isConnected();
    if (isOnlineNotifier.value != connected) {
      isOnlineNotifier.value = connected;
    }
    return connected;
  }

  /// Arka planda periyodik ağ izlemeyi başlatır
  static void startMonitoring({Duration interval = const Duration(seconds: 4)}) {
    _pollingTimer?.cancel();
    checkConnection();
    _pollingTimer = Timer.periodic(interval, (_) => checkConnection());
  }

  /// Ağ izlemeyi durdurur
  static void stopMonitoring() {
    _pollingTimer?.cancel();
    _pollingTimer = null;
  }

  /// İnternet bağlantısı olmadığında açılan şık "İnternete Bağlanın" uyarı penceresi
  static void showNoInternetDialog(
    BuildContext context, {
    String? title,
    String? message,
    VoidCallback? onRetry,
  }) {
    showDialog(
      context: context,
      barrierDismissible: true,
      builder: (dialogContext) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        title: Row(
          children: [
            Container(
              padding: const EdgeInsets.all(8),
              decoration: BoxDecoration(
                color: const Color(0xFFEF4444).withValues(alpha: 0.15),
                shape: BoxShape.circle,
              ),
              child: const Icon(
                Icons.wifi_off_rounded,
                color: Color(0xFFEF4444),
                size: 26,
              ),
            ),
            const SizedBox(width: 12),
            Expanded(
              child: Text(
                title ?? 'İnternete Bağlanın',
                style: const TextStyle(
                  color: Colors.white,
                  fontSize: 18,
                  fontWeight: FontWeight.bold,
                ),
              ),
            ),
          ],
        ),
        content: Text(
          message ??
              'Giriş yapabilmek için lütfen internete bağlanın.\n\nİnternet bağlantınızı kontrol edip tekrar deneyin.',
          style: const TextStyle(
            color: Color(0xFFCBD5E1),
            fontSize: 14,
            height: 1.45,
          ),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(dialogContext),
            child: const Text(
              'Tamam',
              style: TextStyle(color: Color(0xFF94A3B8)),
            ),
          ),
          if (onRetry != null)
            ElevatedButton.icon(
              onPressed: () async {
                Navigator.pop(dialogContext);
                final connected = await isConnected();
                if (connected) {
                  onRetry();
                } else if (context.mounted) {
                  showNoInternetSnackBar(
                    context,
                    message: 'İnternet bağlantısı yok! Lütfen internete bağlanın.',
                  );
                }
              },
              icon: const Icon(Icons.refresh_rounded, size: 16),
              label: const Text('Tekrar Dene'),
              style: ElevatedButton.styleFrom(
                backgroundColor: const Color(0xFF6366F1),
                foregroundColor: Colors.white,
                shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
              ),
            ),
        ],
      ),
    );
  }

  /// Kayan kırmızı SnackBar uyarısı
  static void showNoInternetSnackBar(
    BuildContext context, {
    String message = 'İnternet bağlantısı yok! Lütfen internete bağlanın.',
  }) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.wifi_off_rounded, color: Colors.white),
            const SizedBox(width: 10),
            Expanded(
              child: Text(
                message,
                style: const TextStyle(fontWeight: FontWeight.w500),
              ),
            ),
          ],
        ),
        backgroundColor: const Color(0xFFEF4444),
        behavior: SnackBarBehavior.floating,
        duration: const Duration(seconds: 4),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
        action: SnackBarAction(
          label: 'Yenile',
          textColor: Colors.white,
          onPressed: () => checkConnection(),
        ),
      ),
    );
  }
}
