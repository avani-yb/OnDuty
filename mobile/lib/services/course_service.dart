import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'package:latlong2/latlong.dart';

import '../services/auth_service.dart';

final courseServiceProvider = Provider<CourseService>((ref) {
  return CourseService(ref.read(authServiceProvider));
});

/// Gère les `Course` (le "voyage" réel : une demande + un trajet matchés
/// avec un transporteur donné). À ne pas confondre avec `Demande` (la
/// requête initiale du client, avant sélection d'un transporteur) :
/// c'est bien l'id de la Course qu'il faut utiliser pour le paiement,
/// le suivi, et la confirmation de livraison.
class CourseService {
  final AuthService _authService;

  CourseService(this._authService);

  Dio get _dio => _authService.dio;

  /// Le client sélectionne un trajet proposé par le matching : crée la
  /// Course correspondante. Retourne la Course créée (avec son id réel).
  Future<Course> createCourse({
    required String demandeId,
    required String trajetId,
  }) async {
    final response = await _dio.post(
      '/courses/',
      queryParameters: {'demande_id': demandeId},
      data: {'trajet_id': trajetId},
    );
    return Course.fromJson(response.data);
  }

  Future<List<Course>> getMyCourses() async {
    final response = await _dio.get('/courses/');
    return (response.data as List).map((e) => Course.fromJson(e)).toList();
  }

  Future<Course> getCourse(String id) async {
    final response = await _dio.get('/courses/$id/');
    return Course.fromJson(response.data);
  }

  /// Le transporteur accepte la réservation telle quelle.
  Future<Course> accepter(String id) async {
    final response = await _dio.post('/courses/$id/accepter/');
    return Course.fromJson(response.data);
  }

  /// Le transporteur propose une autre somme que celle du client (avant
  /// d'accepter). La course passe en attente de validation du client.
  Future<Course> proposerMontant(String id, double montant) async {
    final response = await _dio.post('/courses/$id/proposer-montant/', data: {
      'montant': montant,
    });
    return Course.fromJson(response.data);
  }

  /// Le client valide la nouvelle somme proposée par le transporteur.
  Future<Course> validerMontant(String id) async {
    final response = await _dio.post('/courses/$id/valider-montant/');
    return Course.fromJson(response.data);
  }

  /// Le client annule (RM-02 : sans condition ni pénalité — le
  /// remboursement, si un paiement existe déjà, est automatique côté serveur).
  Future<Course> annuler(String id) async {
    final response = await _dio.post('/courses/$id/annuler/');
    return Course.fromJson(response.data);
  }

  /// Le transporteur fait avancer le statut : 'depart', 'en_route' ou 'arrivee'.
  Future<Course> avancerStatut(String id, String action) async {
    final response = await _dio.post('/courses/$id/$action/');
    return Course.fromJson(response.data);
  }

  /// L'expéditeur, ou le destinataire inscrit, confirme la réception :
  /// le prix de la course est versé au transporteur.
  Future<Course> confirmerReception(String id) async {
    final response = await _dio.post('/courses/$id/confirmer_reception/');
    return Course.fromJson(response.data);
  }

  /// Le transporteur choisit une demande compatible avec son trajet. Sans
  /// [montant], le prix proposé par le client est repris. Le client doit
  /// ensuite accepter (puis payer) ou refuser.
  Future<Course> proposer({
    required String demandeId,
    required String trajetId,
    double? montant,
  }) async {
    final response = await _dio.post('/courses/proposer/', data: {
      'demande_id': demandeId,
      'trajet_id': trajetId,
      'montant': ?montant,
    });
    return Course.fromJson(response.data);
  }

  /// Dernière position du transporteur et trajet parcouru (du départ à la livraison).
  Future<SuiviCourse> getSuivi(String courseId) async {
    final response = await _dio.get('/courses/$courseId/suivi/');
    return SuiviCourse.fromJson(response.data);
  }

  /// Le transporteur signale un incident (le client est notifié).
  Future<void> signalerIncident(String courseId, String description) async {
    await _dio.post('/incidents/', data: {'course_id': courseId, 'description': description});
  }
}

class Course {
  final String id;
  final String statut;
  final double montantConvenu;
  final Map<String, dynamic> demande;
  final Map<String, dynamic> trajet;
  final Map<String, dynamic> client;
  final Map<String, dynamic> transporteur;
  final Map<String, dynamic>? destinataire;

  /// Place de l'utilisateur connecté : 'client', 'transporteur' ou 'destinataire'.
  final String? role;
  final String initieePar;
  final String motifAnnulation;
  final bool peutConfirmerReception;

  /// Position du transporteur visible (du départ jusqu'à la livraison).
  final bool suiviDisponible;
  final Map<String, dynamic>? detailsVisuels;
  final String? typeVehicule;
  final Map<String, dynamic>? paiement;
  final DateTime? dateCreation;
  final DateTime? dateDepartReel;
  final DateTime? dateLivraison;

  Course({
    required this.id,
    required this.statut,
    required this.montantConvenu,
    required this.demande,
    required this.trajet,
    required this.client,
    required this.transporteur,
    this.destinataire,
    this.role,
    this.initieePar = 'client',
    this.motifAnnulation = '',
    this.peutConfirmerReception = false,
    this.suiviDisponible = false,
    this.detailsVisuels,
    this.typeVehicule,
    this.paiement,
    this.dateCreation,
    this.dateDepartReel,
    this.dateLivraison,
  });

  bool get estClient => role == 'client';
  bool get estTransporteur => role == 'transporteur';
  bool get estDestinataire => role == 'destinataire';

  factory Course.fromJson(Map<String, dynamic> json) {
    Map<String, dynamic>? mapOuNull(dynamic valeur) =>
        valeur is Map ? Map<String, dynamic>.from(valeur) : null;
    return Course(
      id: json['id'].toString(),
      statut: json['statut'],
      montantConvenu: (json['montant_convenu'] as num?)?.toDouble() ?? 0,
      demande: Map<String, dynamic>.from(json['demande'] ?? {}),
      trajet: Map<String, dynamic>.from(json['trajet'] ?? {}),
      client: Map<String, dynamic>.from(json['client'] ?? {}),
      transporteur: Map<String, dynamic>.from(json['transporteur'] ?? {}),
      destinataire: mapOuNull(json['destinataire']),
      role: json['role'] as String?,
      initieePar: (json['initiee_par'] as String?) ?? 'client',
      motifAnnulation: (json['motif_annulation'] as String?) ?? '',
      peutConfirmerReception: json['peut_confirmer_reception'] == true,
      suiviDisponible: json['suivi_disponible'] == true,
      detailsVisuels: mapOuNull(json['details_visuels']),
      typeVehicule: json['type_vehicule'] as String?,
      paiement: mapOuNull(json['paiement']),
      dateCreation: json['date_creation'] != null ? DateTime.tryParse(json['date_creation']) : null,
      dateDepartReel: json['date_depart_reel'] != null ? DateTime.tryParse(json['date_depart_reel']) : null,
      dateLivraison: json['date_livraison'] != null ? DateTime.tryParse(json['date_livraison']) : null,
    );
  }
}

/// Suivi GPS d'une course : dernière position et trajet parcouru.
class SuiviCourse {
  final bool actif;
  final LatLng? position;
  final DateTime? dateDernierePosition;
  final List<LatLng> trace;

  SuiviCourse({required this.actif, this.position, this.dateDernierePosition, this.trace = const []});

  factory SuiviCourse.fromJson(Map<String, dynamic> json) {
    final derniere = json['derniere_position'] as Map<String, dynamic>?;
    return SuiviCourse(
      actif: json['actif'] == true,
      position: derniere == null
          ? null
          : LatLng((derniere['latitude'] as num).toDouble(), (derniere['longitude'] as num).toDouble()),
      dateDernierePosition: derniere == null ? null : DateTime.tryParse(derniere['date'] as String),
      trace: ((json['trace'] as List?) ?? [])
          .map((p) => LatLng((p[0] as num).toDouble(), (p[1] as num).toDouble()))
          .toList(),
    );
  }
}
