import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/auth_service.dart';

final paymentServiceProvider = Provider<PaymentService>((ref) {
  return PaymentService(ref.read(authServiceProvider));
});

/// Paiement d'une course via CamPay (MTN MoMo / Orange Money). Toute la
/// communication avec CamPay passe par le backend : aucune clé dans l'app.
class PaymentService {
  final AuthService _authService;

  PaymentService(this._authService);

  Dio get _dio => _authService.dio;

  /// Détail du montant à payer : prix, commission, frais, total, numéro proposé.
  Future<Devis> getDevis(String courseId) async {
    final response = await _dio.get('/paiements/devis/', queryParameters: {'course_id': courseId});
    return Devis.fromJson(response.data);
  }

  /// Paiement existant pour la course, ou null.
  Future<Paiement?> getPaiementCourse(String courseId) async {
    final response = await _dio.get('/paiements/', queryParameters: {'course_id': courseId});
    final results = response.data as List;
    return results.isEmpty ? null : Paiement.fromJson(results.first);
  }

  /// Lance le paiement : le client reçoit une demande de validation sur son
  /// téléphone (code USSD, ex. *126#).
  Future<Paiement> payer({required String courseId, required String numero}) async {
    final response = await _dio.post(
      '/paiements/',
      queryParameters: {'course_id': courseId},
      data: {'numero': numero},
    );
    return Paiement.fromJson(response.data);
  }

  /// Demande au serveur si le paiement a été validé.
  Future<Paiement> verifier(String paiementId) async {
    final response = await _dio.post('/paiements/$paiementId/verifier/');
    return Paiement.fromJson(response.data);
  }

  /// Historique : paiements effectués (client) et courses payées (transporteur).
  Future<List<Paiement>> getMyPayments() async {
    final response = await _dio.get('/paiements/');
    return (response.data as List).map((e) => Paiement.fromJson(e)).toList();
  }
}

class Devis {
  final double montantCourse;
  final double tauxCommission;
  final double commission;
  final double frais;
  final double total;
  final String numeroDefaut;

  Devis({
    required this.montantCourse,
    required this.tauxCommission,
    required this.commission,
    required this.frais,
    required this.total,
    required this.numeroDefaut,
  });

  factory Devis.fromJson(Map<String, dynamic> json) {
    double n(dynamic v) => (v as num?)?.toDouble() ?? 0;
    return Devis(
      montantCourse: n(json['montant_course']),
      tauxCommission: n(json['taux_commission']),
      commission: n(json['commission']),
      frais: n(json['frais']),
      total: n(json['total']),
      numeroDefaut: (json['numero_defaut'] as String?) ?? '',
    );
  }
}

class Paiement {
  final String id;

  /// 'en_attente', 'echoue', 'bloque_escrow', 'libere' ou 'rembourse'.
  final String statut;

  /// Libellé prêt à afficher, adapté au rôle (client / transporteur).
  final String statutAffiche;
  final String role;
  final double montantCourse;
  final double? montant;
  final String methode;
  final String codeUssd;
  final String messageErreur;
  final Map<String, dynamic> course;
  final DateTime? dateCreation;

  Paiement({
    required this.id,
    required this.statut,
    required this.statutAffiche,
    required this.role,
    required this.montantCourse,
    required this.montant,
    required this.methode,
    required this.codeUssd,
    required this.messageErreur,
    required this.course,
    this.dateCreation,
  });

  bool get enAttente => statut == 'en_attente';
  bool get echoue => statut == 'echoue';
  bool get estPaye => statut == 'bloque_escrow' || statut == 'libere';

  factory Paiement.fromJson(Map<String, dynamic> json) {
    return Paiement(
      id: json['id'].toString(),
      statut: json['statut'],
      statutAffiche: (json['statut_affiche'] as String?) ?? json['statut'],
      role: (json['role'] as String?) ?? 'client',
      montantCourse: (json['montant_course'] as num?)?.toDouble() ?? 0,
      montant: (json['montant'] as num?)?.toDouble(),
      methode: (json['methode'] as String?) ?? '',
      codeUssd: (json['code_ussd'] as String?) ?? '',
      messageErreur: (json['message_erreur'] as String?) ?? '',
      course: Map<String, dynamic>.from(json['course'] ?? {}),
      dateCreation: json['date_creation'] != null ? DateTime.tryParse(json['date_creation']) : null,
    );
  }
}
