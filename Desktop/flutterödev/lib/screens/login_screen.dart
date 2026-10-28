import 'package:flutter/material.dart';
import '../services/database_helper.dart';
import '../services/network_service.dart';
import '../services/preference_service.dart';
import '../widgets/custom_text_field.dart';
import '../widgets/offline_banner.dart';
import 'forgot_password_screen.dart';
import 'home_screen.dart';
import 'register_screen.dart';

/// [LoginScreen], kullanıcının kayıtlı e-posta ve şifresi ile sisteme giriş yaptığı ekrandır.
///
/// Başlıca Görevleri:
/// - E-posta formatı ve şifre zorunluluk kontrolleri (Form Validation).
/// - "Beni Hatırla" (Remember Me) seçeneği ile e-posta ve şifrenin yerel hafızada tutulması.
/// - SQLite veritabanı üzerinden kullanıcı ve SHA-256 şifre doğrulaması.
/// - Başarılı girişte [HomeScreen] sayfasına geçiş yapılması.
class LoginScreen extends StatefulWidget {
  const LoginScreen({super.key});

  @override
  State<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends State<LoginScreen> {
  // Formun geçerlilik durumunu yönetmek için GlobalKey
  final _formKey = GlobalKey<FormState>();

  // Form metin kutuları denetleyicileri (Controllers)
  final _emailController = TextEditingController();
  final _passwordController = TextEditingController();

  // "Beni Hatırla" onay kutusunun durumu (true/false)
  bool _rememberMe = false;

  // Giriş işlemi sürerken dönen yükleme göstergesi durumu
  bool _isLoading = false;

  @override
  void initState() {
    super.initState();
    // Ekran ilk yüklendiğinde hafızada kayıtlı "Beni Hatırla" verisi var mı kontrol et
    _loadSavedCredentials();
    // Ekran ilk açıldığında internet durumunu kontrol et
    WidgetsBinding.instance.addPostFrameCallback((_) {
      _checkInitialConnectivity();
    });
  }

  /// Ekran ilk açıldığında internet yoksa kullanıcıyı uyarır
  Future<void> _checkInitialConnectivity() async {
    final isOnline = await NetworkService.isConnected();
    if (!isOnline && mounted) {
      NetworkService.showNoInternetSnackBar(
        context,
        message: 'İnternet bağlantısı yok! Lütfen internete bağlanın.',
      );
    }
  }

  /// SharedPreferences üzerinden daha önce kaydedilmiş "Beni Hatırla" verilerini çeker.
  /// Eğer kayıtlı e-posta veya şifre varsa kutucukları otomatik doldurur.
  Future<void> _loadSavedCredentials() async {
    final remember = await PreferenceService.isRememberMeEnabled();
    if (remember) {
      final savedEmail = await PreferenceService.getSavedEmail();
      final savedPassword = await PreferenceService.getSavedPassword();

      if (mounted) {
        setState(() {
          _rememberMe = true;
          if (savedEmail != null) _emailController.text = savedEmail;
          if (savedPassword != null) _passwordController.text = savedPassword;
        });
      }
    }
  }

  @override
  void dispose() {
    // Bellek sızıntısını (Memory Leak) önlemek için denetleyicileri serbest bırakıyoruz
    _emailController.dispose();
    _passwordController.dispose();
    super.dispose();
  }

  /// Giriş Yap butonuna basıldığında tetiklenen ana metot
  Future<void> _handleLogin() async {
    // 1. İnternet bağlantısı kontrolü
    final isOnline = await NetworkService.isConnected();
    if (!isOnline) {
      if (mounted) {
        NetworkService.showNoInternetDialog(
          context,
          title: 'İnternete Bağlanın',
          message:
              'Giriş yapabilmek için lütfen internete bağlanın.\n\nİnternet bağlantınızı kontrol edip tekrar deneyin.',
          onRetry: () => _handleLogin(),
        );
        NetworkService.showNoInternetSnackBar(
          context,
          message: 'Lütfen internete bağlanın! Giriş yapılamadı.',
        );
      }
      return;
    }

    // 2. Form alanlarının doğruluğunu (validation) kontrol et
    if (!_formKey.currentState!.validate()) return;

    // Yükleniyor durumunu aktifleştir (Butonda spinner gösterilir)
    setState(() => _isLoading = true);

    final email = _emailController.text.trim();
    final password = _passwordController.text;

    try {
      // 2. Veritabanından kullanıcıyı ve SHA-256 ile özetlenmiş şifreyi sorgula
      final result = await DatabaseHelper.instance.loginUser(
        email: email,
        password: password,
      );

      // Asenkron işlem sonrası widget ağaçtan ayrıldıysa işlemi durdur
      if (!mounted) return;

      if (result['success'] == true) {
        final user = result['user'];

        // 3. "Beni Hatırla" tercihini kaydet veya temizle
        await PreferenceService.saveRememberMe(
          remember: _rememberMe,
          email: email,
          password: _rememberMe ? password : null,
        );

        // 4. Giriş yapan kullanıcının aktif oturumunu sakla
        await PreferenceService.saveCurrentSession(
          name: user.name,
          email: user.email,
        );

        if (!mounted) return;

        // Başarılı giriş bildirim mesajı (Yeşil SnackBar)
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Row(
              children: [
                const Icon(Icons.check_circle_rounded, color: Colors.white),
                const SizedBox(width: 10),
                Text('Hoş geldiniz, ${user.name}!'),
              ],
            ),
            backgroundColor: const Color(0xFF10B981),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
        );

        // 5. Ana Ekrana (HomeScreen) geçiş yap ve geri dönüşü engelle (Replacement)
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(
            builder: (context) => HomeScreen(user: user),
          ),
        );
      } else {
        // Hatalı şifre veya bulunamayan e-posta bildirimi (Kırmızı SnackBar)
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Row(
              children: [
                const Icon(Icons.error_outline_rounded, color: Colors.white),
                const SizedBox(width: 10),
                Expanded(child: Text(result['message'] ?? 'Giriş başarısız')),
              ],
            ),
            backgroundColor: const Color(0xFFEF4444),
            behavior: SnackBarBehavior.floating,
            shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(10)),
          ),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text('Bir hata meydana geldi: $e'),
            backgroundColor: const Color(0xFFEF4444),
          ),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  /// "Şifremi Unuttum" tıklandığında Şifre Sıfırlama Ekranına yönlendirir
  Future<void> _openForgotPasswordScreen() async {
    final currentEmail = _emailController.text.trim();
    final updatedEmail = await Navigator.push<String?>(
      context,
      MaterialPageRoute(
        builder: (context) => ForgotPasswordScreen(
          initialEmail: currentEmail.isNotEmpty ? currentEmail : null,
        ),
      ),
    );

    // Eğer şifre sıfırlanıp e-posta ile geri dönüldüyse e-postayı doldur ve şifreyi temizle
    if (updatedEmail != null && updatedEmail.isNotEmpty && mounted) {
      setState(() {
        _emailController.text = updatedEmail;
        _passwordController.clear();
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: const Color(0xFF0F172A),
      body: SafeArea(
        child: Column(
          children: [
            // İnternet kesildiğinde gösterilen kırmızı uyarı bandı
            const OfflineBanner(),
            Expanded(
              child: Center(
                child: SingleChildScrollView(
                  physics: const BouncingScrollPhysics(),
                  padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 12),
                  child: ConstrainedBox(
                    // Büyük ekranlarda (Web/Tablet/Masaüstü) formun çok genişlemesini engelliyoruz
                    constraints: const BoxConstraints(maxWidth: 440),
                    child: Form(
                key: _formKey,
                child: Column(
                  mainAxisAlignment: MainAxisAlignment.center,
                  crossAxisAlignment: CrossAxisAlignment.stretch,
                  children: [
                    // ===== 1. ÜST İKON VE BAŞLIK ALANI =====
                    Center(
                      child: Container(
                        width: 80,
                        height: 80,
                        decoration: BoxDecoration(
                          gradient: const LinearGradient(
                            colors: [Color(0xFF6366F1), Color(0xFF8B5CF6)],
                            begin: Alignment.topLeft,
                            end: Alignment.bottomRight,
                          ),
                          shape: BoxShape.circle,
                          boxShadow: [
                            BoxShadow(
                              color: const Color(0xFF6366F1).withValues(alpha: 0.4),
                              blurRadius: 20,
                              offset: const Offset(0, 10),
                            ),
                          ],
                        ),
                        child: const Icon(
                          Icons.lock_person_rounded,
                          size: 42,
                          color: Colors.white,
                        ),
                      ),
                    ),
                    const SizedBox(height: 24),
                    const Text(
                      'Tekrar Hoş Geldiniz!',
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
                      'Lütfen hesabınıza erişmek için bilgilerinizi girin',
                      textAlign: TextAlign.center,
                      style: TextStyle(
                        fontSize: 14,
                        color: Color(0xFF94A3B8),
                      ),
                    ),
                    const SizedBox(height: 32),

                    // ===== İNTERNET YOKKEN GİRİŞTE GÖRÜNEN DİKKAT ÇEKİCİ UYARI KARTI =====
                    ValueListenableBuilder<bool>(
                      valueListenable: NetworkService.isOnlineNotifier,
                      builder: (context, isOnline, child) {
                        if (isOnline) return const SizedBox.shrink();
                        return Container(
                          margin: const EdgeInsets.only(bottom: 20),
                          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
                          decoration: BoxDecoration(
                            color: const Color(0xFFEF4444).withValues(alpha: 0.15),
                            borderRadius: BorderRadius.circular(12),
                            border: Border.all(
                              color: const Color(0xFFEF4444).withValues(alpha: 0.4),
                            ),
                          ),
                          child: const Row(
                            children: [
                              Icon(
                                Icons.wifi_off_rounded,
                                color: Color(0xFFEF4444),
                                size: 22,
                              ),
                              SizedBox(width: 12),
                              Expanded(
                                child: Column(
                                  crossAxisAlignment: CrossAxisAlignment.start,
                                  children: [
                                    Text(
                                      'İnternet Bağlantısı Yok',
                                      style: TextStyle(
                                        color: Colors.white,
                                        fontSize: 13.5,
                                        fontWeight: FontWeight.bold,
                                      ),
                                    ),
                                    SizedBox(height: 2),
                                    Text(
                                      'Giriş yapabilmek için lütfen internete bağlanın.',
                                      style: TextStyle(
                                        color: Color(0xFFFCA5A5),
                                        fontSize: 12,
                                      ),
                                    ),
                                  ],
                                ),
                              ),
                            ],
                          ),
                        );
                      },
                    ),

                    // ===== 2. E-POSTA GİRİŞ ALANI =====
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
                        // E-posta regex doğrulama kontrolü
                        final emailRegex = RegExp(r'^[\w-\.]+@([\w-]+\.)+[\w-]{2,4}$');
                        if (!emailRegex.hasMatch(value.trim())) {
                          return 'Geçerli bir e-posta adresi girin';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 18),

                    // ===== 3. ŞİFRE GİRİŞ ALANI =====
                    CustomTextField(
                      controller: _passwordController,
                      label: 'Şifre',
                      hint: '••••••••',
                      prefixIcon: Icons.lock_outline_rounded,
                      isPassword: true,
                      textInputAction: TextInputAction.done,
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Lütfen şifrenizi girin';
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 12),

                    // ===== 4. BENİ HATIRLA & ŞİFREMİ UNUTTUM SATIRI =====
                    Row(
                      mainAxisAlignment: MainAxisAlignment.spaceBetween,
                      children: [
                        // Beni Hatırla Seçim Kutusu
                        InkWell(
                          onTap: () {
                            setState(() {
                              _rememberMe = !_rememberMe;
                            });
                          },
                          borderRadius: BorderRadius.circular(8),
                          child: Padding(
                            padding: const EdgeInsets.symmetric(vertical: 4),
                            child: Row(
                              children: [
                                SizedBox(
                                  width: 24,
                                  height: 24,
                                  child: Checkbox(
                                    value: _rememberMe,
                                    activeColor: const Color(0xFF6366F1),
                                    checkColor: Colors.white,
                                    side: const BorderSide(
                                      color: Color(0xFF64748B),
                                      width: 1.5,
                                    ),
                                    shape: RoundedRectangleBorder(
                                      borderRadius: BorderRadius.circular(6),
                                    ),
                                    onChanged: (value) {
                                      setState(() {
                                        _rememberMe = value ?? false;
                                      });
                                    },
                                  ),
                                ),
                                const SizedBox(width: 8),
                                const Text(
                                  'Beni Hatırla',
                                  style: TextStyle(
                                    color: Color(0xFFCBD5E1),
                                    fontSize: 14,
                                    fontWeight: FontWeight.w500,
                                  ),
                                ),
                              ],
                            ),
                          ),
                        ),

                        // Şifremi Unuttum Butonu (Artık çalışan şifre sıfırlama ekranını açar)
                        TextButton(
                          onPressed: _openForgotPasswordScreen,
                          style: TextButton.styleFrom(
                            padding: EdgeInsets.zero,
                            minimumSize: Size.zero,
                            tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                          ),
                          child: const Text(
                            'Şifremi Unuttum?',
                            style: TextStyle(
                              color: Color(0xFF818CF8),
                              fontSize: 13,
                              fontWeight: FontWeight.w600,
                            ),
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 28),

                    // ===== 5. GİRİŞ YAP BUTONU =====
                    Container(
                      height: 52,
                      decoration: BoxDecoration(
                        gradient: const LinearGradient(
                          colors: [Color(0xFF6366F1), Color(0xFF4F46E5)],
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
                        onPressed: _isLoading ? null : _handleLogin,
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
                                'Giriş Yap',
                                style: TextStyle(
                                  color: Colors.white,
                                  fontSize: 16,
                                  fontWeight: FontWeight.bold,
                                  letterSpacing: 0.5,
                                ),
                              ),
                      ),
                    ),
                    const SizedBox(height: 24),

                    // ===== 6. KAYIT OL EKRANINA GEÇİŞ LİNKİ =====
                    Wrap(
                      alignment: WrapAlignment.center,
                      crossAxisAlignment: WrapCrossAlignment.center,
                      children: [
                        const Text(
                          'Hesabınız yok mu?',
                          style: TextStyle(
                            color: Color(0xFF94A3B8),
                            fontSize: 14,
                          ),
                        ),
                        TextButton(
                          onPressed: () {
                            // Kayıt ekranına geçiş yap
                            Navigator.push(
                              context,
                              MaterialPageRoute(
                                builder: (context) => const RegisterScreen(),
                              ),
                            );
                          },
                          child: const Text(
                            'Hemen Kayıt Ol',
                            style: TextStyle(
                              color: Color(0xFF818CF8),
                              fontSize: 14,
                              fontWeight: FontWeight.bold,
                            ),
                          ),
                        ),
                      ],
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
