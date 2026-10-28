/// [UserModel] sınıfı, uygulamada kayıt olan ve giriş yapan kullanıcıların
/// verilerini (Ad, E-posta, şifrelenmiş şifre, kayıt tarihi ve veritabanı ID'si)
/// temsil eden veri modelidir.
class UserModel {
  /// Veritabanındaki benzersiz birincil anahtar (Primary Key).
  /// Yeni kayıt oluşturulurken henüz atanmadığı için null olabilir.
  final int? id;

  /// Kullanıcının tam adı ve soyadı
  final String name;

  /// Kullanıcının sisteme giriş yaparken kullandığı benzersiz e-posta adresi
  final String email;

  /// Güvenlik amacıyla düz metin yerine SHA-256 ile özetlenmiş (hash'lenmiş) şifre
  final String passwordHash;

  /// Kullanıcının kayıt olduğu tarih ve saat (ISO-8601 formatında metin)
  final String createdAt;

  /// UserModel kurucu (constructor) metodu
  UserModel({
    this.id,
    required this.name,
    required this.email,
    required this.passwordHash,
    required this.createdAt,
  });

  /// Nesneyi veritabanına (SQLite) eklemek üzere Map formatına dönüştürür.
  /// E-posta adresini küçük harfe çevirip boşluklardan arındırır (normalizasyon).
  Map<String, dynamic> toMap() {
    return {
      if (id != null) 'id': id,
      'name': name,
      'email': email.trim().toLowerCase(),
      'passwordHash': passwordHash,
      'createdAt': createdAt,
    };
  }

  /// Veritabanından çekilen Map (anahtar-değer) verisini UserModel nesnesine dönüştürür.
  factory UserModel.fromMap(Map<String, dynamic> map) {
    return UserModel(
      id: map['id'] is int ? map['id'] as int : int.tryParse(map['id'].toString()),
      name: map['name'] as String? ?? '',
      email: map['email'] as String? ?? '',
      passwordHash: map['passwordHash'] as String? ?? '',
      createdAt: map['createdAt'] as String? ?? '',
    );
  }
}
