import 'package:flutter/material.dart';
import '../models/user_model.dart';
import '../services/database_helper.dart';
import '../services/preference_service.dart';
import '../widgets/offline_banner.dart';
import 'login_screen.dart';

/// [HomeScreen], kullanıcı başarılı bir şekilde giriş yaptıktan sonra yönlendirildiği ana paneldir.
///
/// Başlıca Görevleri:
/// - Giriş yapan kullanıcının Ad, E-posta ve Veritabanı ID bilgilerini göstermek.
/// - "Beni Hatırla" tercihinin o anda aktif olup olmadığını göstermek.
/// - Güvenlik ve SHA-256 şifreleme hakkında bilgi kartı sunmak.
/// - Veritabanındaki tüm kullanıcıları listeleyen test modal penceresini (`_showDatabaseUsersModal`) açmak.
/// - Oturumu sonlandırma (Logout) ve Giriş ekranına yönlendirme.
class HomeScreen extends StatefulWidget {
  /// Giriş yapmış aktif kullanıcı nesnesi
  final UserModel user;

  const HomeScreen({
    super.key,
    required this.user,
  });

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  // "Beni Hatırla" özelliğinin cihazda açık olup olmadığını tutar
  bool _isRememberMeActive = false;

  // Veritabanındaki toplam kayıtlı kullanıcı sayısı
  int _totalUserCount = 0;

  @override
  void initState() {
    super.initState();
    // Sayfa açıldığında Beni Hatırla durumunu ve kullanıcı sayısını çek
    _loadDetails();
  }

  /// SharedPreferences ve SQLite üzerinden özet istatistikleri yükler
  Future<void> _loadDetails() async {
    final remember = await PreferenceService.isRememberMeEnabled();
    final count = await DatabaseHelper.instance.getUserCount();
    if (mounted) {
      setState(() {
        _isRememberMeActive = remember;
        _totalUserCount = count;
      });
    }
  }

  /// Oturumu Kapatma (Logout) İşlemi
  /// Kullanıcıya emin olup olmadığını soran onay diyaloğu açar
  Future<void> _handleLogout() async {
    final shouldLogout = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        backgroundColor: const Color(0xFF1E293B),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(18)),
        title: const Text('Çıkış Yapılsın mı?', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold)),
        content: const Text(
          'Oturumunuz sonlandırılacaktır. Devam etmek istiyor musunuz?',
          style: TextStyle(color: Color(0xFF94A3B8)),
        ),
        actions: [
          TextButton(
            onPressed: () => Navigator.pop(context, false),
            child: const Text('İptal', style: TextStyle(color: Color(0xFF94A3B8))),
          ),
          ElevatedButton(
            onPressed: () => Navigator.pop(context, true),
            style: ElevatedButton.styleFrom(
              backgroundColor: const Color(0xFFEF4444),
              shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
            ),
            child: const Text('Çıkış Yap', style: TextStyle(color: Colors.white)),
          ),
        ],
      ),
    );

    // Kullanıcı onayladıysa aktif oturumu sil ve Giriş ekranına dön
    if (shouldLogout == true) {
      await PreferenceService.clearSession();
      if (!mounted) return;

      // Tüm sayfa geçmişini silip LoginScreen'i en başa koyuyoruz (pushAndRemoveUntil)
      Navigator.pushAndRemoveUntil(
        context,
        MaterialPageRoute(builder: (context) => const LoginScreen()),
        (route) => false,
      );
    }
  }

  /// ÖDEV SUNUMU TESTİ: SQLite veritabanındaki tüm kayıtları gösteren alt pencere (Modal BottomSheet)
  /// Bu fonksiyon sayesinde öğretmen veya değerlendirici veritabanının çalıştığını canlı görebilir
  Future<void> _showDatabaseUsersModal() async {
    final users = await DatabaseHelper.instance.getAllUsers();

    if (!mounted) return;

    showModalBottomSheet(
      context: context,
      backgroundColor: const Color(0xFF1E293B),
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(24)),
      ),
      builder: (context) {
        return DraggableScrollableSheet(
          initialChildSize: 0.65,
          minChildSize: 0.4,
          maxChildSize: 0.9,
          expand: false,
          builder: (context, scrollController) {
            return Padding(
              padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  // Sürüklenebilir tutamak çizgisi
                  Center(
                    child: Container(
                      width: 40,
                      height: 4,
                      decoration: BoxDecoration(
                        color: const Color(0xFF64748B),
                        borderRadius: BorderRadius.circular(4),
                      ),
                    ),
                  ),
                  const SizedBox(height: 16),

                  // Başlık ve Kayıt Sayısı Rozeti
                  Row(
                    mainAxisAlignment: MainAxisAlignment.spaceBetween,
                    children: [
                      const Text(
                        'Veritabanı Kayıtları',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.bold,
                        ),
                      ),
                      Container(
                        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 4),
                        decoration: BoxDecoration(
                          color: const Color(0xFF6366F1).withValues(alpha: 0.2),
                          borderRadius: BorderRadius.circular(8),
                          border: Border.all(color: const Color(0xFF6366F1)),
                        ),
                        child: Text(
                          '${users.length} Kayıt',
                          style: const TextStyle(
                            color: Color(0xFF818CF8),
                            fontSize: 12,
                            fontWeight: FontWeight.bold,
                          ),
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 8),
                  const Text(
                    'SQLite veritabanında depolanan kayıtlı kullanıcılar:',
                    style: TextStyle(color: Color(0xFF94A3B8), fontSize: 13),
                  ),
                  const Divider(color: Color(0xFF334155), height: 24),

                  // Kullanıcılar Listesi
                  Expanded(
                    child: users.isEmpty
                        ? const Center(
                            child: Text(
                              'Henüz kayıtlı kullanıcı bulunmuyor.',
                              style: TextStyle(color: Color(0xFF94A3B8)),
                            ),
                          )
                        : ListView.separated(
                            controller: scrollController,
                            itemCount: users.length,
                            separatorBuilder: (context, index) => const SizedBox(height: 10),
                            itemBuilder: (context, index) {
                              final u = users[index];
                              // O an açık olan kullanıcı mı kontrolü
                              final isCurrent = u.email.toLowerCase() == widget.user.email.toLowerCase();

                              return Container(
                                padding: const EdgeInsets.all(12),
                                decoration: BoxDecoration(
                                  color: isCurrent
                                      ? const Color(0xFF6366F1).withValues(alpha: 0.15)
                                      : const Color(0xFF0F172A),
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(
                                    color: isCurrent
                                        ? const Color(0xFF6366F1)
                                        : const Color(0xFF334155),
                                    width: isCurrent ? 1.5 : 1,
                                  ),
                                ),
                                child: Row(
                                  children: [
                                    // Kullanıcı İsminin Baş Harfi
                                    CircleAvatar(
                                      radius: 20,
                                      backgroundColor: isCurrent
                                          ? const Color(0xFF6366F1)
                                          : const Color(0xFF334155),
                                      child: Text(
                                        u.name.isNotEmpty ? u.name[0].toUpperCase() : '?',
                                        style: const TextStyle(
                                          color: Colors.white,
                                          fontWeight: FontWeight.bold,
                                        ),
                                      ),
                                    ),
                                    const SizedBox(width: 12),
                                    Expanded(
                                      child: Column(
                                        crossAxisAlignment: CrossAxisAlignment.start,
                                        children: [
                                          Row(
                                            children: [
                                              Flexible(
                                                child: Text(
                                                  u.name,
                                                  style: const TextStyle(
                                                    color: Colors.white,
                                                    fontSize: 14,
                                                    fontWeight: FontWeight.bold,
                                                  ),
                                                  overflow: TextOverflow.ellipsis,
                                                ),
                                              ),
                                              if (isCurrent) ...[
                                                const SizedBox(width: 6),
                                                Container(
                                                  padding: const EdgeInsets.symmetric(horizontal: 6, vertical: 2),
                                                  decoration: BoxDecoration(
                                                    color: const Color(0xFF10B981),
                                                    borderRadius: BorderRadius.circular(6),
                                                  ),
                                                  child: const Text(
                                                    'Aktif',
                                                    style: TextStyle(
                                                      color: Colors.white,
                                                      fontSize: 10,
                                                      fontWeight: FontWeight.bold,
                                                    ),
                                                  ),
                                                ),
                                              ],
                                            ],
                                          ),
                                          const SizedBox(height: 2),
                                          Text(
                                            u.email,
                                            style: const TextStyle(
                                              color: Color(0xFF94A3B8),
                                              fontSize: 12,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                    // Kullanıcının Veritabanı ID'si
                                    Text(
                                      'ID: #${u.id ?? "-"}',
                                      style: const TextStyle(
                                        color: Color(0xFF64748B),
                                        fontSize: 12,
                                        fontWeight: FontWeight.w600,
                                      ),
                                    ),
                                  ],
                                ),
                              );
                            },
                          ),
                  ),
                ],
              ),
            );
          },
        );
      },
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        title: const Text(
          'Ana Sayfa',
          style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold),
        ),
        actions: [
          // Çıkış Yap Butonu
          IconButton(
            icon: const Icon(Icons.logout_rounded, color: Color(0xFFEF4444)),
            tooltip: 'Çıkış Yap',
            onPressed: _handleLogout,
          ),
        ],
      ),
      body: SafeArea(
        child: Column(
          children: [
            // İnternet kesildiğinde çıkan uyarı bandı
            const OfflineBanner(),
            Expanded(
              child: Center(
                child: SingleChildScrollView(
                  physics: const BouncingScrollPhysics(),
                  padding: const EdgeInsets.symmetric(horizontal: 20, vertical: 16),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 520),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.stretch,
                      children: [
                // ===== 1. HOŞ GELDİNİZ KARTI (Vibrant Indigo-Violet Gradient) =====
                Container(
                  padding: const EdgeInsets.all(22),
                  decoration: BoxDecoration(
                    gradient: const LinearGradient(
                      colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                      begin: Alignment.topLeft,
                      end: Alignment.bottomRight,
                    ),
                    borderRadius: BorderRadius.circular(22),
                    boxShadow: [
                      BoxShadow(
                        color: const Color(0xFF6366F1).withValues(alpha: 0.35),
                        blurRadius: 20,
                        offset: const Offset(0, 10),
                      ),
                    ],
                  ),
                  child: Row(
                    children: [
                      // Kullanıcı Profil Baş Harfi
                      CircleAvatar(
                        radius: 32,
                        backgroundColor: Colors.white.withValues(alpha: 0.2),
                        child: Text(
                          widget.user.name.isNotEmpty ? widget.user.name[0].toUpperCase() : 'U',
                          style: const TextStyle(
                            fontSize: 28,
                            fontWeight: FontWeight.bold,
                            color: Colors.white,
                          ),
                        ),
                      ),
                      const SizedBox(width: 18),
                      // Kullanıcı Bilgileri Metinleri
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Hoş Geldiniz 👋',
                              style: TextStyle(
                                color: Colors.white70,
                                fontSize: 14,
                                fontWeight: FontWeight.w500,
                              ),
                            ),
                            const SizedBox(height: 4),
                            Text(
                              widget.user.name,
                              style: const TextStyle(
                                color: Colors.white,
                                fontSize: 20,
                                fontWeight: FontWeight.bold,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                            const SizedBox(height: 4),
                            Text(
                              widget.user.email,
                              style: TextStyle(
                                color: Colors.white.withValues(alpha: 0.85),
                                fontSize: 13,
                              ),
                              overflow: TextOverflow.ellipsis,
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                // ===== 2. ÖZET BİLGİ VE AYAR KARTLARI =====
                const Text(
                  'Özet Bilgiler',
                  style: TextStyle(
                    color: Colors.white,
                    fontSize: 16,
                    fontWeight: FontWeight.bold,
                  ),
                ),
                const SizedBox(height: 12),

                // Beni Hatırla Durum Kartı
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFF334155)),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: _isRememberMeActive
                              ? const Color(0xFF10B981).withValues(alpha: 0.15)
                              : const Color(0xFF64748B).withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: Icon(
                          _isRememberMeActive ? Icons.check_circle_outline : Icons.cancel_outlined,
                          color: _isRememberMeActive ? const Color(0xFF10B981) : const Color(0xFF94A3B8),
                          size: 24,
                        ),
                      ),
                      const SizedBox(width: 14),
                      Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            const Text(
                              'Beni Hatırla Özelliği',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            const SizedBox(height: 2),
                            Text(
                              _isRememberMeActive
                                  ? 'Aktif (Giriş bilgileriniz cihazda kayıtlı)'
                                  : 'Pasif (Her girişte bilgi istenecektir)',
                              style: const TextStyle(
                                color: Color(0xFF94A3B8),
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),

                // Veritabanı ve Güvenlik Bilgi Kartı
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B),
                    borderRadius: BorderRadius.circular(16),
                    border: Border.all(color: const Color(0xFF334155)),
                  ),
                  child: Row(
                    children: [
                      Container(
                        padding: const EdgeInsets.all(10),
                        decoration: BoxDecoration(
                          color: const Color(0xFF6366F1).withValues(alpha: 0.15),
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(
                          Icons.shield_outlined,
                          color: Color(0xFF818CF8),
                          size: 24,
                        ),
                      ),
                      const SizedBox(width: 14),
                      const Expanded(
                        child: Column(
                          crossAxisAlignment: CrossAxisAlignment.start,
                          children: [
                            Text(
                              'Güvenlik & Şifreleme',
                              style: TextStyle(
                                color: Colors.white,
                                fontSize: 14,
                                fontWeight: FontWeight.w600,
                              ),
                            ),
                            SizedBox(height: 2),
                            Text(
                              'Şifreniz SHA-256 algoritmasıyla şifrelenerek saklanmaktadır.',
                              style: TextStyle(
                                color: Color(0xFF94A3B8),
                                fontSize: 12,
                              ),
                            ),
                          ],
                        ),
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 24),

                // ===== 3. VERİTABANI KAYITLARINI GÖR BUTONU =====
                Container(
                  height: 50,
                  decoration: BoxDecoration(
                    color: const Color(0xFF1E293B),
                    borderRadius: BorderRadius.circular(14),
                    border: Border.all(color: const Color(0xFF475569)),
                  ),
                  child: TextButton.icon(
                    onPressed: _showDatabaseUsersModal,
                    icon: const Icon(Icons.storage_rounded, color: Color(0xFF818CF8)),
                    label: Text(
                      'Kayıtlı Kullanıcıları Gör ($_totalUserCount Kayıt)',
                      style: const TextStyle(
                        color: Colors.white,
                        fontSize: 15,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ),
                ),
                const SizedBox(height: 14),

                // ===== 4. OTURUMU KAPAT BUTONU =====
                OutlinedButton.icon(
                  onPressed: _handleLogout,
                  icon: const Icon(Icons.logout_rounded, color: Color(0xFFEF4444), size: 18),
                  label: const Text(
                    'Oturumu Kapat',
                    style: TextStyle(
                      color: Color(0xFFEF4444),
                      fontSize: 15,
                      fontWeight: FontWeight.w600,
                    ),
                  ),
                  style: OutlinedButton.styleFrom(
                    side: const BorderSide(color: Color(0xFFEF4444), width: 1.2),
                    padding: const EdgeInsets.symmetric(vertical: 14),
                    shape: RoundedRectangleBorder(
                      borderRadius: BorderRadius.circular(14),
                    ),
                  ),
                ),
              ],
            ),
          ),
        ),
      ),
    ),
  ],
),
),
);
  }
}
