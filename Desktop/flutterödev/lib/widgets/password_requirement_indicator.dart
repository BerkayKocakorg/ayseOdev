import 'package:flutter/material.dart';

/// [PasswordRequirementIndicator], kullanıcının şifre yazarken ödevde istenen kurallara
/// uyup uymadığını anlık (real-time) olarak görselleştiren bir widget'tır.
///
/// Kontrol Edilen Kurallar:
/// 1. En az 6 karakter uzunluk
/// 2. En az bir büyük harf (A-Z)
/// 3. En az bir küçük harf (a-z)
class PasswordRequirementIndicator extends StatelessWidget {
  /// Kullanıcının o an metin kutusuna girdiği şifre
  final String password;

  const PasswordRequirementIndicator({
    super.key,
    required this.password,
  });

  /// Kural 1: Şifre en az 6 karakter mi?
  bool get hasMinLength => password.length >= 6;

  /// Kural 2: Şifre en az bir büyük harf (A-Z) içeriyor mu? (Regex kontrolü)
  bool get hasUppercase => RegExp(r'[A-Z]').hasMatch(password);

  /// Kural 3: Şifre en az bir küçük harf (a-z) içeriyor mu? (Regex kontrolü)
  bool get hasLowercase => RegExp(r'[a-z]').hasMatch(password);

  /// Şifrenin tüm kuralları eksiksiz sağlayıp sağlamadığını kontrol eden statik metot.
  /// Form doğrulama (Validation) aşamasında da çağrılır.
  static bool isValid(String password) {
    return password.length >= 6 &&
        RegExp(r'[A-Z]').hasMatch(password) &&
        RegExp(r'[a-z]').hasMatch(password);
  }

  @override
  Widget build(BuildContext context) {
    // Şifre alanı boşsa gösterge alanını gizle
    if (password.isEmpty) {
      return const SizedBox.shrink();
    }

    return Container(
      margin: const EdgeInsets.only(top: 8, bottom: 8),
      padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
      decoration: BoxDecoration(
        color: const Color(0xFF1E293B).withValues(alpha: 0.6),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(
          color: const Color(0xFF334155),
          width: 1,
        ),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          const Text(
            'Şifre Güvenlik Kriterleri:',
            style: TextStyle(
              color: Color(0xFF94A3B8),
              fontSize: 12,
              fontWeight: FontWeight.w600,
            ),
          ),
          const SizedBox(height: 8),

          // Kriter 1: Minimum 6 karakter kontrolü
          _buildItem(
            isMet: hasMinLength,
            label: 'En az 6 karakter',
          ),
          const SizedBox(height: 6),

          // Kriter 2: Büyük harf kontrolü
          _buildItem(
            isMet: hasUppercase,
            label: 'En az bir büyük harf (A-Z)',
          ),
          const SizedBox(height: 6),

          // Kriter 3: Küçük harf kontrolü
          _buildItem(
            isMet: hasLowercase,
            label: 'En az bir küçük harf (a-z)',
          ),
        ],
      ),
    );
  }

  /// Kriter satırını oluşturan yardımcı metot:
  /// - Kriter sağlanmışsa: Yeşil yuvarlak içinde onay ikonu (✓) ve yeşil metin
  /// - Kriter henüz sağlanmamışsa: Gri daire ve gri metin
  Widget _buildItem({required bool isMet, required String label}) {
    return Row(
      children: [
        AnimatedContainer(
          duration: const Duration(milliseconds: 250),
          width: 18,
          height: 18,
          decoration: BoxDecoration(
            shape: BoxShape.circle,
            color: isMet ? const Color(0xFF10B981) : const Color(0xFF475569),
          ),
          child: Icon(
            isMet ? Icons.check : Icons.circle,
            size: isMet ? 12 : 6,
            color: Colors.white,
          ),
        ),
        const SizedBox(width: 10),
        Text(
          label,
          style: TextStyle(
            color: isMet ? const Color(0xFF10B981) : const Color(0xFF94A3B8),
            fontSize: 13,
            fontWeight: isMet ? FontWeight.w600 : FontWeight.normal,
          ),
        ),
      ],
    );
  }
}
