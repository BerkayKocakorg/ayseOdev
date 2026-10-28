import 'package:flutter/material.dart';

/// [CustomTextField], uygulamadaki tüm metin girdi alanlarında (E-posta, Ad Soyad, Şifre vb.)
/// tutarlı, şık ve modern bir tasarım dili sağlayan özel form bileşenidir.
///
/// Özellikleri:
/// - Başlık etiketi (Label) ve sol tarafında bilgilendirici ikon (prefixIcon).
/// - Şifre alanları için açılıp kapanabilir göz ikonu (Show/Hide password).
/// - Hata durumlarında kırmızı kenarlık ve açıklayıcı hata mesajı.
/// - Odaklanma (Focus) durumunda parlak mor-indigo kenarlık efekti.
class CustomTextField extends StatefulWidget {
  /// Metin kutusunun içeriğini kontrol eden denetleyici
  final TextEditingController controller;

  /// Metin kutusunun üzerinde görünen alan adı (örn: "E-posta Adresi")
  final String label;

  /// Metin kutusu boşken görünen ipucu metni (örn: "ornek@email.com")
  final String hint;

  /// Metin kutusunun solundaki simge
  final IconData prefixIcon;

  /// Alanın şifre alanı olup olmadığı (true ise karakterler gizlenir)
  final bool isPassword;

  /// Klavye türü (E-posta için emailAddress, metin için text vb.)
  final TextInputType keyboardType;

  /// Klavyedeki onay butonu eylemi (Sonraki alana geç veya Tamamla)
  final TextInputAction textInputAction;

  /// Form doğrulama fonksiyonu (Hatalıysa hata mesajı, geçerliyse null döner)
  final String? Function(String?)? validator;

  /// Metin her değiştiğinde tetiklenen geri çağırım fonksiyonu
  final void Function(String)? onChanged;

  const CustomTextField({
    super.key,
    required this.controller,
    required this.label,
    required this.hint,
    required this.prefixIcon,
    this.isPassword = false,
    this.keyboardType = TextInputType.text,
    this.textInputAction = TextInputAction.next,
    this.validator,
    this.onChanged,
  });

  @override
  State<CustomTextField> createState() => _CustomTextFieldState();
}

class _CustomTextFieldState extends State<CustomTextField> {
  /// Şifrenin gizli (noktalı) mı yoksa görünür mü olduğunu tutan durum değişkeni
  bool _obscureText = true;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        // Alan Başlığı
        Text(
          widget.label,
          style: const TextStyle(
            color: Color(0xFFE2E8F0),
            fontSize: 14,
            fontWeight: FontWeight.w600,
            letterSpacing: 0.3,
          ),
        ),
        const SizedBox(height: 8),

        // Metin Giriş Alanı (TextFormField)
        TextFormField(
          controller: widget.controller,
          // Şifre alanıysa _obscureText durumuna göre karakterleri gizle/göster
          obscureText: widget.isPassword ? _obscureText : false,
          keyboardType: widget.keyboardType,
          textInputAction: widget.textInputAction,
          validator: widget.validator,
          onChanged: widget.onChanged,
          style: const TextStyle(
            color: Colors.white,
            fontSize: 15,
            fontWeight: FontWeight.w500,
          ),
          decoration: InputDecoration(
            hintText: widget.hint,
            hintStyle: TextStyle(
              color: const Color(0xFF94A3B8).withValues(alpha: 0.6),
              fontSize: 14,
            ),
            filled: true,
            fillColor: const Color(0xFF1E293B).withValues(alpha: 0.7),
            // Sol İkon
            prefixIcon: Icon(
              widget.prefixIcon,
              color: const Color(0xFF818CF8),
              size: 22,
            ),
            // Şifre alanıysa sağ tarafa göz ikonu ekle
            suffixIcon: widget.isPassword
                ? IconButton(
                    icon: Icon(
                      _obscureText ? Icons.visibility_off_outlined : Icons.visibility_outlined,
                      color: const Color(0xFF94A3B8),
                      size: 20,
                    ),
                    onPressed: () {
                      setState(() {
                        _obscureText = !_obscureText;
                      });
                    },
                  )
                : null,
            contentPadding: const EdgeInsets.symmetric(horizontal: 18, vertical: 16),
            // Normal (Varsayılan) Kenarlık
            enabledBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(
                color: Color(0xFF334155),
                width: 1.2,
              ),
            ),
            // Odaklanıldığında Parlayan Kenarlık
            focusedBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(
                color: Color(0xFF6366F1),
                width: 2,
              ),
            ),
            // Hata Durumundaki Kırmızı Kenarlık
            errorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(
                color: Color(0xFFEF4444),
                width: 1.5,
              ),
            ),
            // Odaklanılmış Hata Durumu Kenarlığı
            focusedErrorBorder: OutlineInputBorder(
              borderRadius: BorderRadius.circular(14),
              borderSide: const BorderSide(
                color: Color(0xFFEF4444),
                width: 2,
              ),
            ),
            errorStyle: const TextStyle(
              color: Color(0xFFF87171),
              fontSize: 12,
              fontWeight: FontWeight.w500,
            ),
          ),
        ),
      ],
    );
  }
}
