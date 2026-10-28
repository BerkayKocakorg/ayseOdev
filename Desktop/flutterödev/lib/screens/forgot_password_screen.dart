import 'package:flutter/material.dart';
import '../services/database_helper.dart';
import '../services/network_service.dart';
import '../services/preference_service.dart';
import '../widgets/custom_text_field.dart';
import '../widgets/offline_banner.dart';
import '../widgets/password_requirement_indicator.dart';

/// [ForgotPasswordScreen], kullanıcının unuttuğu şifresini güvenli bir şekilde
/// sıfırlamasını (Password Reset) sağlayan ekrandır.
///
/// Başlıca Görevleri:
/// - İnternet bağlantısını kontrol etmek (Bağlantı yoksa "internete bağlı değilsiniz" uyarısı verir).
/// - Kayıtlı e-posta adresinin sistemde var olup olmadığını doğrulamak.
/// - Yeni şifrenin ödev kurallarına (En az 6 karakter, büyük harf, küçük harf) uygunluğunu
///   canlı olarak [PasswordRequirementIndicator] ile denetlemek.
/// - Şifre tekrar uyuşmasını kontrol etmek.
/// - Şifreyi SHA-256 ile özetleyip veritabanında güncellemek.
class ForgotPasswordScreen extends StatefulWidget {
  /// Giriş ekranında daha önce yazılmış e-posta varsa otomatik doldurmak için
  final String? initialEmail;

  const ForgotPasswordScreen({
    super.key,
    this.initialEmail,
  });

  @override
  State<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends State<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();

  final _emailController = TextEditingController();
  final _newPasswordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();

  String _currentNewPassword = '';
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    if (widget.initialEmail != null && widget.initialEmail!.trim().isNotEmpty) {
      _emailController.text = widget.initialEmail!.trim();
    }
  }

  @override
  void dispose() {
    _emailController.dispose();
    _newPasswordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  /// Şifre sıfırlama işlemini yürüten ana fonksiyon
  Future<void> _handleResetPassword() async {
    // 1. İNTERNET BAĞLANTISI KONTROLÜ
    final isOnline = await NetworkService.isConnected();
    if (!isOnline) {
      if (mounted) {
        NetworkService.showNoInternetDialog(
          context,
          title: 'İnternete Bağlanın',
          message:
              'Şifrenizi sıfırlayabilmek için lütfen internete bağlanın.\n\nİnternet bağlantınızı kontrol edip tekrar deneyin.',
          onRetry: () => _handleResetPassword(),
        );
        NetworkService.showNoInternetSnackBar(
          context,
          message: 'Lütfen internete bağlanın! Şifre sıfırlanamadı.',
        );
      }
      return;
    }

    // 2. Form alanlarının doğruluğunu kontrol et
    if (!_formKey.currentState!.validate()) return;

    final email = _emailController.text.trim();
    final newPassword = _newPasswordController.text;
    final confirmPassword = _confirmPasswordController.text;

    // 3. ÖDEV KURALI 1: En az 6 karakter
    if (newPassword.length < 6) {
      _showErrorSnackBar('Yeni şifreniz en az 6 karakter olmalıdır.');
      return;
    }

    // 4. ÖDEV KURALI 2: En az bir büyük harf (A-Z)
    if (!RegExp(r'[A-Z]').hasMatch(newPassword)) {
      _showErrorSnackBar('Yeni şifreniz en az bir büyük harf (A-Z) içermelidir.');
      return;
    }

    // 5. ÖDEV KURALI 3: En az bir küçük harf (a-z)
    if (!RegExp(r'[a-z]').hasMatch(newPassword)) {
      _showErrorSnackBar('Yeni şifreniz en az bir küçük harf (a-z) içermelidir.');
      return;
    }

    // 6. Şifrelerin eşleştiğini kontrol et
    if (newPassword != confirmPassword) {
      _showErrorSnackBar('Girdiğiniz yeni şifreler birbiriyle eşleşmiyor.');
      return;
    }

    setState(() => _isLoading = true);

    try {
      // 7. Veritabanında şifreyi güncelle (SHA-256 ile özetlenerek kaydedilir)
      final result = await DatabaseHelper.instance.resetPassword(
        email: email,
        newPassword: newPassword,
      );

      if (!mounted) return;

      if (result['success'] == true) {
        // Eğer "Beni Hatırla" bu kullanıcıya aitse hafızadaki şifreyi de güncelle
        await PreferenceService.updateSavedPasswordIfMatches(email, newPassword);

        if (!mounted) return;

        // Başarı mesajı (Yeşil SnackBar)
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Row(
              children: [
                const Icon(Icons.check_circle_rounded, color: Colors.white),
                const SizedBox(width: 10),
                Expanded(
                  child: Text(
                    result['message'] ?? 'Şifreniz başarıyla güncellendi!',
                  ),
                ),
              ],
            ),
            backgroundColor: const Color(0xFF10B981),
            behavior: SnackBarBehavior.floating,
            duration: const Duration(seconds: 4),
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
        );

        // Giriş ekranına dön ve e-postayı aktar
        Navigator.pop(context, email);
      } else {
        // Hata durumunda kullanıcıyı uyar (örn: E-posta bulunamadı)
        _showErrorSnackBar(result['message'] ?? 'Şifre güncellenemedi.');
      }
    } catch (e) {
      if (mounted) {
        _showErrorSnackBar('Bir hata meydana geldi: $e');
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

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
          'Şifremi Sıfırla',
          style: TextStyle(color: Colors.white, fontSize: 18, fontWeight: FontWeight.w600),
        ),
        centerTitle: true,
      ),
      body: SafeArea(
        child: Column(
          children: [
            // Çevrimdışı uyarı bandı
            const OfflineBanner(),
            Expanded(
              child: Center(
                child: SingleChildScrollView(
                  physics: const BouncingScrollPhysics(),
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  child: ConstrainedBox(
                    constraints: const BoxConstraints(maxWidth: 440),
                    child: Form(
                      key: _formKey,
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.stretch,
                        children: [
                          // 1. ÜST İKON VE AÇIKLAMA
                          Center(
                            child: Container(
                              width: 76,
                              height: 76,
                              decoration: BoxDecoration(
                                gradient: const LinearGradient(
                                  colors: [Color(0xFF6366F1), Color(0xFFEC4899)],
                                  begin: Alignment.topLeft,
                                  end: Alignment.bottomRight,
                                ),
                                shape: BoxShape.circle,
                                boxShadow: [
                                  BoxShadow(
                                    color: const Color(0xFFEC4899).withValues(alpha: 0.35),
                                    blurRadius: 18,
                                    offset: const Offset(0, 8),
                                  ),
                                ],
                              ),
                              child: const Icon(
                                Icons.lock_reset_rounded,
                                size: 40,
                                color: Colors.white,
                              ),
                            ),
                          ),
                          const SizedBox(height: 20),
                          const Text(
                            'Yeni Şifre Belirleyin',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 24,
                              fontWeight: FontWeight.bold,
                              color: Colors.white,
                              letterSpacing: -0.5,
                            ),
                          ),
                          const SizedBox(height: 8),
                          const Text(
                            'Kayıtlı e-posta adresinizi ve yeni şifrenizi girerek hesabınızın şifresini güncelleyin.',
                            textAlign: TextAlign.center,
                            style: TextStyle(
                              fontSize: 13.5,
                              color: Color(0xFF94A3B8),
                              height: 1.4,
                            ),
                          ),
                          const SizedBox(height: 28),

                          // 2. E-POSTA ALANI
                          CustomTextField(
                            controller: _emailController,
                            label: 'Kayıtlı E-posta Adresi',
                            hint: 'ornek@email.com',
                            prefixIcon: Icons.email_outlined,
                            keyboardType: TextInputType.emailAddress,
                            validator: (value) {
                              if (value == null || value.trim().isEmpty) {
                                return 'Lütfen kayıtlı e-posta adresinizi girin';
                              }
                              final emailRegex = RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$');
                              if (!emailRegex.hasMatch(value.trim())) {
                                return 'Geçerli bir e-posta adresi girin';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 18),

                          // 3. YENİ ŞİFRE ALANI
                          CustomTextField(
                            controller: _newPasswordController,
                            label: 'Yeni Şifre',
                            hint: 'En az 6 karakter, büyük & küçük harf',
                            prefixIcon: Icons.lock_outline_rounded,
                            isPassword: true,
                            onChanged: (val) {
                              setState(() {
                                _currentNewPassword = val;
                              });
                            },
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Lütfen yeni şifrenizi girin';
                              }
                              if (value.length < 6) {
                                return 'Şifre en az 6 karakter olmalıdır';
                              }
                              if (!RegExp(r'[A-Z]').hasMatch(value)) {
                                return 'Şifre en az bir büyük harf içermelidir';
                              }
                              if (!RegExp(r'[a-z]').hasMatch(value)) {
                                return 'Şifre en az bir küçük harf içermelidir';
                              }
                              return null;
                            },
                          ),

                          // Canlı Şifre Kriter Göstergesi
                          PasswordRequirementIndicator(
                            password: _currentNewPassword,
                          ),

                          const SizedBox(height: 16),

                          // 4. YENİ ŞİFRE TEKRAR ALANI
                          CustomTextField(
                            controller: _confirmPasswordController,
                            label: 'Yeni Şifre Tekrar',
                            hint: 'Yeni şifrenizi tekrar girin',
                            prefixIcon: Icons.lock_reset_rounded,
                            isPassword: true,
                            textInputAction: TextInputAction.done,
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return 'Lütfen yeni şifrenizi tekrar girin';
                              }
                              if (value != _newPasswordController.text) {
                                return 'Şifreler eşleşmiyor';
                              }
                              return null;
                            },
                          ),
                          const SizedBox(height: 28),

                          // 5. ŞİFREYİ GÜNCELLE BUTONU
                          Container(
                            height: 52,
                            decoration: BoxDecoration(
                              gradient: const LinearGradient(
                                colors: [Color(0xFF6366F1), Color(0xFFEC4899)],
                                begin: Alignment.centerLeft,
                                end: Alignment.centerRight,
                              ),
                              borderRadius: BorderRadius.circular(14),
                              boxShadow: [
                                BoxShadow(
                                  color: const Color(0xFF6366F1).withValues(alpha: 0.35),
                                  blurRadius: 15,
                                  offset: const Offset(0, 6),
                                ),
                              ],
                            ),
                            child: ElevatedButton(
                              onPressed: _isLoading ? null : _handleResetPassword,
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
                                      'Şifremi Güncelle',
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

                          // 6. GİRİŞ EKRANINA DÖNÜŞ LİNKİ
                          Center(
                            child: TextButton.icon(
                              onPressed: () => Navigator.pop(context),
                              icon: const Icon(Icons.arrow_back_rounded, size: 16, color: Color(0xFF818CF8)),
                              label: const Text(
                                'Giriş Ekranına Dön',
                                style: TextStyle(
                                  color: Color(0xFF818CF8),
                                  fontSize: 14,
                                  fontWeight: FontWeight.w600,
                                ),
                              ),
                            ),
                          ),
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
