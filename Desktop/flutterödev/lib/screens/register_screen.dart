import 'package:flutter/material.dart';
import '../services/database_helper.dart';
import '../services/network_service.dart';
import '../widgets/custom_text_field.dart';
import '../widgets/offline_banner.dart';
import '../widgets/password_requirement_indicator.dart';

/// [RegisterScreen], yeni kullanıcıların sisteme kaydolduğu ekrandır.
///
/// Başlıca Görevleri:
/// - Ad Soyad, E-posta, Şifre ve Şifre Tekrar verilerini toplamak.
/// - Ödev kuralı olan şifre kriterlerini (En az 6 karakter, büyük harf ve küçük harf) denetlemek.
/// - Kullanıcı şifreyi yazarken canlı kriter göstergesi (`PasswordRequirementIndicator`) ile geri bildirim sunmak.
/// - Şifre tekrar uyuşmasını kontrol etmek.
/// - Aynı e-posta adresiyle daha önce kayıt yapılıp yapılmadığını denetlemek.
/// - Başarılı kayıtta şifreyi SHA-256 ile özetleyip SQLite veritabanına eklemek ve Giriş ekranına dönmek.
class RegisterScreen extends StatefulWidget {
  const RegisterScreen({super.key});

  @override
  State<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends State<RegisterScreen> {
  // Form doğrulama anahtarı
  final _formKey = GlobalKey<FormState>();

  // Form metin kutuları denetleyicileri
  final _nameController = TextEditingController();
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  // Canlı şifre kriter göstergesine gönderilen anlık şifre metni
  String _currentPassword = '';

  // Kayıt işlemi sürerken butonda spinner gösterme durumu
  bool _isLoading = false;

  @override
  void dispose() {
    // Bellek sızıntılarını önlemek için tüm denetleyicileri dispose ediyoruz
    _nameController.dispose();
    _emailController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  /// Kayıt Ol butonuna basıldığında tetiklenen kayıt metodu
  Future<void> _handleRegister() async {
    // 1. İNTERNET BAĞLANTISI KONTROLÜ
    final isOnline = await NetworkService.isConnected();
    if (!isOnline) {
      if (mounted) {
        NetworkService.showNoInternetDialog(
          context,
          title: 'İnternete Bağlanın',
          message:
              'Kayıt olabilmek için lütfen internete bağlanın.\n\nİnternet bağlantınızı kontrol edip tekrar deneyin.',
          onRetry: () => _handleRegister(),
        );
        NetworkService.showNoInternetSnackBar(
          context,
          message: 'Lütfen internete bağlanın! Kayıt yapılamadı.',
        );
      }
      return;
    }

    // 2. Form alanlarının boş olup olmadığını denetle
    if (!_formKey.currentState!.validate()) return;

    final password = _passwordController.text;

    // 2. ÖDEV KURALI 1: Şifre en az 6 karakter olmalıdır
    if (password.length < 6) {
      _showErrorSnackBar('Şifreniz en az 6 karakterden oluşmalıdır.');
      return;
    }

    // 3. ÖDEV KURALI 2: Şifre en az bir büyük harf (A-Z) içermelidir
    if (!RegExp(r'[A-Z]').hasMatch(password)) {
      _showErrorSnackBar('Şifreniz en az bir büyük harf (A-Z) içermelidir.');
      return;
    }

    // 4. ÖDEV KURALI 3: Şifre en az bir küçük harf (a-z) içermelidir
    if (!RegExp(r'[a-z]').hasMatch(password)) {
      _showErrorSnackBar('Şifreniz en az bir küçük harf (a-z) içermelidir.');
      return;
    }

    // 5. Şifre ve Şifre Tekrar alanlarının birebir aynı olduğunu kontrol et
    if (password != _confirmPasswordController.text) {
      _showErrorSnackBar('Girdiğiniz şifreler birbiriyle eşleşmiyor.');
      return;
    }

    // Yükleniyor durumunu aktifleştir
    setState(() => _isLoading = true);

    try {
      // 6. Veritabanına kayıt isteği gönder (E-posta kontrolü ve SHA-256 şifreleme içeride yapılır)
      final result = await DatabaseHelper.instance.registerUser(
        name: _nameController.text.trim(),
        email: _emailController.text.trim(),
        password: password,
      );

      if (!mounted) return;

      if (result['success'] == true) {
        // Başarılı kayıt bildirimi (Yeşil SnackBar)
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Row(
              children: [
                const Icon(Icons.check_circle_rounded, color: Colors.white),
                const SizedBox(width: 10),
                const Expanded(
                  child: Text('Kayıt başarılı! Şimdi giriş yapabilirsiniz.'),
                ),
              ],
            ),
            backgroundColor: const Color(0xFF10B981),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
        );

        // Giriş ekranına otomatik geri dön
        Navigator.pop(context);
      } else {
        // Hata durumunda (örn. E-posta zaten varsa) kullanıcıyı bilgilendir
        _showErrorSnackBar(result['message'] ?? 'Kayıt başarısız oldu.');
      }
    } catch (e) {
      if (mounted) {
        _showErrorSnackBar('Bir hata oluştu: $e');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  /// Hata mesajlarını ekranda şık bir kırmızı SnackBar ile gösteren yardımcı fonksiyon
  void _showErrorSnackBar(String message) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(
        content: Row(
          children: [
            const Icon(Icons.warning_amber_rounded, color: Colors.white),
            const SizedBox(width: 10),
            Expanded(child: Text(message)),
          ],
        ),
        backgroundColor: const Color(0xFFEF4444),
        behavior: SnackBarBehavior.floating,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      appBar: AppBar(
        backgroundColor: Colors.transparent,
        elevation: 0,
        leading: IconButton(
          icon: const Icon(Icons.arrow_back_ios_new_rounded, color: Colors.white, size: 20),
          onPressed: () => Navigator.pop(context),
        ),
        title: const Text(
          'Kayıt Ol',
          style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600),
        ),
        centerTitle: true,
      ),
      body: SafeArea(
        child: Column(
          children: [
            // İnternet bağlantısı koptuğunda gösterilen kırmızı uyarı bandı
            const OfflineBanner(),
            Expanded(
              child: Center(
                child: SingleChildScrollView(
                  physics: const BouncingScrollPhysics(),
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 10),
                  child: ConstrainedBox(
                    // Masaüstü ve geniş ekranlarda maksimum form genişliğini sınırlıyoruz
                    constraints: const BoxConstraints(maxWidth: 440),
                    child: Form(
                key: _formKey,
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // ===== 1. BAŞLIK VE AÇIKLAMA ALANI =====
                    const Text(
                      'Yeni Hesap Oluşturun',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 26,
                        fontWeight: FontWeight.bold,
                        color: Colors.white,
                        letterSpacing: -0.5,
                      ),
                    ),
                    const SizedBox(height: 8),
                    const Text(
                      'Kullanıcı bilgilerinizi girerek hızlıca kaydolun',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 14,
                        color: Color(0xFF94A3B8),
                      ),
                    ),
                    const SizedBox(height: 28),

                    // ===== 2. AD SOYAD ALANI =====
                    CustomTextField(
                      controller: _nameController,
                      label: 'Ad Soyad',
                      hint: 'Adınız Soyadınız',
                      prefixIcon: Icons.person_outline_rounded,
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'Lütfen adınızı ve soyadınızı girin';
                        }
                        if (value.trim().length < 3) {
                          return 'Ad Soyad en az 3 karakter olmalıdır';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    // ===== 3. E-POSTA ALANI =====
                    CustomTextField(
                      controller: _emailController,
                      label: 'E-posta Adresi',
                      hint: 'ornek@email.com',
                      prefixIcon: Icons.email_outlined,
                      keyboardType: TextInputType.emailAddress,
                      validator: (value) {
                        if (value == null || value.trim().isEmpty) {
                          return 'Lütfen e-posta adresinizi girin';
                        }
                        final emailRegex = RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$');
                        if (!emailRegex.hasMatch(value.trim())) {
                          return 'Lütfen geçerli bir e-posta adresi girin';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),

                    // ===== 4. ŞİFRE ALANI (En az 6 karakter, Büyük & Küçük Harf) =====
                    CustomTextField(
                      controller: _passwordController,
                      label: 'Şifre',
                      hint: 'En az 6 karakter, büyük & küçük harf',
                      prefixIcon: Icons.lock_outline_rounded,
                      isPassword: true,
                      onChanged: (val) {
                        // Kullanıcı her tuşa bastığında canlı kriter göstergesini güncelle
                        setState(() {
                          _currentPassword = val;
                        });
                      },
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Lütfen şifrenizi girin';
                        }
                        if (value.length < 6) {
                          return 'Şifre en az 6 karakter olmalıdır';
                        }
                        if (!RegExp(r'[A-Z]').hasMatch(value)) {
                          return 'Şifre en az bir büyük harf (A-Z) içermelidir';
                        }
                        if (!RegExp(r'[a-z]').hasMatch(value)) {
                          return 'Şifre en az bir küçük harf (a-z) içermelidir';
                        }
                        return null;
                      },
                    ),

                    // ===== 5. CANLI ŞİFRE KRİTER GÖSTERGESİ =====
                    // Kullanıcı şifreyi girdikçe kurallar anlık olarak yeşil onay işaretine döner
                    PasswordRequirementIndicator(
                      password: _currentPassword,
                    ),

                    const SizedBox(height: 14),

                    // ===== 6. ŞİFRE TEKRAR ALANI =====
                    CustomTextField(
                      controller: _confirmPasswordController,
                      label: 'Şifre Tekrar',
                      hint: 'Şifrenizi tekrar girin',
                      prefixIcon: Icons.lock_reset_rounded,
                      isPassword: true,
                      textInputAction: TextInputAction.done,
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Lütfen şifrenizi tekrar girin';
                        }
                        if (value != _passwordController.text) {
                          return 'Şifreler eşleşmiyor';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 28),

                    // ===== 7. KAYIT OL BUTONU =====
                    Container(
                      height: 52,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF8B5CF6), Color(0xFF6366F1)],
                          begin: Alignment.centerLeft,
                          end: Alignment.centerRight,
                        ),
                        borderRadius: BorderRadius.circular(14),
                        boxShadow: [
                          BoxShadow(
                            color: const Color(0xFF8B5CF6).withValues(alpha: 0.35),
                            blurRadius: 15,
                            offset: const Offset(0, 6),
                          ),
                        ],
                      ),
                      child: ElevatedButton(
                        onPressed: _isLoading ? null : _handleRegister,
                        style: ElevatedButton.styleFrom(
                          backgroundColor: Colors.transparent,
                          shadowColor: Colors.transparent,
                          shape: RoundedRectangleBorder(
                            borderRadius: BorderRadius.circular(14),
                          ),
                        ),
                        child: _isLoading
                            ? const SizedBox(
                                width: 22,
                                height: 22,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2.5,
                                  valueColor: AlwaysStoppedAnimation<Color>(Colors.white),
                                ),
                              )
                            : const Text(
                                'Kayıt Ol',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                  letterSpacing: 0.5,
                                ),
                              ),
                      ),
                    ),
                    const SizedBox(height: 20),

                    // ===== 8. ZATEN HESABIN VAR MI? GİRİŞ YAP LİNKİ =====
                    Wrap(
                      alignment: WrapAlignment.center,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        const Text(
                          'Zaten bir hesabınız var mı?',
                          style: TextStyle(
                            color: Color(0xFF94A3B8),
                            fontSize: 14,
                          ),
                        ),
                        TextButton(
                          onPressed: () => Navigator.pop(context),
                          child: const Text(
                            'Giriş Yap',
                            style: TextStyle(
                              color: Color(0xFF818CF8),
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 10),
                  ],
                ),
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
