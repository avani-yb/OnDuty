import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/auth_service.dart';

final kycServiceProvider = Provider<KycService>((ref) {
  return KycService(ref.read(authServiceProvider));
});

/// Vérification d'identité (KYC/CNI). Les photos sont envoyées au backend,
/// qui seul communique avec le fournisseur (Smile Identity) : aucune clé
/// n'est présente dans l'application.
class KycService {
  final AuthService _authService;

  KycService(this._authService);

  Dio get _dio => _authService.dio;

  /// Dernière vérification CNI de l'utilisateur, ou `null` s'il n'en a jamais soumis.
  Future<KycVerification?> getDerniereVerificationCni() async {
    final response = await _dio.get('/verifications/');
    final cni = (response.data as List)
        .map((e) => KycVerification.fromJson(e))
        .where((v) => v.type == 'cni')
        .toList()
      ..sort((a, b) => b.tentative.compareTo(a.tentative));
    return cni.isEmpty ? null : cni.first;
  }

  Future<KycVerification> soumettreCni({
    required File recto,
    required File verso,
    required File selfie,
  }) async {
    final formData = FormData.fromMap({
      'type_verification': 'cni',
      'cni_recto': await MultipartFile.fromFile(recto.path, filename: 'cni_recto.jpg'),
      'cni_verso': await MultipartFile.fromFile(verso.path, filename: 'cni_verso.jpg'),
      'selfie': await MultipartFile.fromFile(selfie.path, filename: 'selfie.jpg'),
    });
    final response = await _dio.post('/verifications/', data: formData);
    return KycVerification.fromJson(response.data);
  }

  /// Demande au backend d'interroger le fournisseur (résultat pas encore reçu).
  Future<KycVerification> actualiser(int id) async {
    final response = await _dio.post('/verifications/$id/actualiser/');
    return KycVerification.fromJson(response.data);
  }
}

class KycVerification {
  final int id;
  final String type;
  final String statut;
  final String motif;
  final int tentative;

  KycVerification({
    required this.id,
    required this.type,
    required this.statut,
    required this.motif,
    required this.tentative,
  });

  bool get estValidee => statut == 'validee';
  bool get estRejetee => statut == 'rejetee';
  bool get estEnCours => statut == 'en_attente' || statut == 'a_revoir';

  factory KycVerification.fromJson(Map<String, dynamic> json) {
    return KycVerification(
      id: json['id'] as int,
      type: json['type_verification'] as String,
      statut: json['statut'] as String,
      motif: (json['motif'] as String?) ?? '',
      tentative: (json['numero_tentative'] as int?) ?? 1,
    );
  }
}
