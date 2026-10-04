import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/auth_service.dart';

final shipmentServiceProvider = Provider<ShipmentService>((ref) {
  return ShipmentService(ref.read(authServiceProvider));
});

/// Demandes d'expédition du client (avant et pendant la course).
class ShipmentService {
  final AuthService _authService;

  ShipmentService(this._authService);

  Dio get _dio => _authService.dio;

  Future<ShipmentCreation> createShipment({
    required String origin,
    required String destination,
    required String description,
    required double weightKg,
    required double montantPropose,
    required DateTime preferredDate,
    required File videoFile,
    String telephoneDestinataire = '',
  }) async {
    final formData = FormData.fromMap({
      'origine': origin,
      'destination': destination,
      'description': description,
      'poids_estime_kg': weightKg,
      'montant_propose': montantPropose,
      'date_souhaitee': preferredDate.toIso8601String(),
      'telephone_destinataire': telephoneDestinataire,
      'video': await MultipartFile.fromFile(videoFile.path),
    });

    final response = await _dio.post('/demandes/', data: formData);
    return ShipmentCreation.fromJson(response.data);
  }

  /// Mes demandes (les demandes supprimées ne sont pas renvoyées).
  Future<List<Shipment>> getMyShipments() async {
    final response = await _dio.get('/demandes/');
    return (response.data as List).map((e) => Shipment.fromJson(e)).toList();
  }

  Future<Shipment> getShipment(String id) async {
    final response = await _dio.get('/demandes/$id/');
    return Shipment.fromJson(response.data);
  }

  /// Modifie une demande. Une nouvelle description ou une nouvelle vidéo
  /// relance le contrôle IA : la réponse contient alors son verdict.
  Future<ShipmentCreation> updateShipment(String id, Map<String, dynamic> champs, {File? video}) async {
    final Object data = video == null
        ? champs
        : FormData.fromMap({...champs, 'video': await MultipartFile.fromFile(video.path)});
    final response = await _dio.patch('/demandes/$id/', data: data);
    return ShipmentCreation.fromJson(response.data);
  }

  Future<void> deleteShipment(String id) async {
    await _dio.delete('/demandes/$id/');
  }

  /// Demande une revue manuelle par l'administrateur d'un rejet de l'IA (BF-08).
  Future<void> contester(String id) async {
    await _dio.post('/demandes/$id/contester/');
  }

  Future<MatchingResult> getMatching(String shipmentId) async {
    final response = await _dio.get('/matching/demande/$shipmentId/');
    return MatchingResult.fromJson(response.data);
  }

  Future<MatchingResult> getMatchingForTrip(String tripId) async {
    final response = await _dio.get('/matching/trajet/$tripId/');
    return MatchingResult.fromJson(response.data);
  }
}

/// Réponse d'une création ou d'une modification : la demande et, si le
/// contrôle IA a été (re)lancé, son verdict ('valide' ou 'rejete').
class ShipmentCreation {
  final Shipment shipment;
  final String? verdict;
  final String? motifRejet;

  ShipmentCreation({required this.shipment, this.verdict, this.motifRejet});

  bool get isRejected => verdict == 'rejete';

  factory ShipmentCreation.fromJson(Map<String, dynamic> json) {
    // Création / nouveau contrôle : {"demande": {...}, "controle_ia": {...}} ;
    // simple modification : la demande directement.
    final demande = json['demande'] is Map ? json['demande'] : json;
    final controle = json['controle_ia'] as Map<String, dynamic>?;
    return ShipmentCreation(
      shipment: Shipment.fromJson(Map<String, dynamic>.from(demande)),
      verdict: controle?['verdict'] as String?,
      motifRejet: controle?['motif_rejet'] as String?,
    );
  }
}

class Shipment {
  final String id;
  final String origin;
  final String destination;
  final String description;
  final double weightKg;
  final double montantPropose;
  final DateTime preferredDate;

  /// 'en_cours_controle', 'rejetee' ou 'publiee'.
  final String status;
  final String videoUrl;
  final String telephoneDestinataire;
  final Map<String, dynamic>? destinataire;

  /// Course non annulée liée à la demande : {id, statut} ou null.
  final Map<String, dynamic>? courseActive;

  /// Dernier contrôle IA : {verdict, motif_rejet, contestation}.
  final Map<String, dynamic>? dernierControle;
  final DateTime createdAt;

  Shipment({
    required this.id,
    required this.origin,
    required this.destination,
    required this.description,
    required this.weightKg,
    required this.montantPropose,
    required this.preferredDate,
    required this.status,
    required this.videoUrl,
    required this.createdAt,
    this.telephoneDestinataire = '',
    this.destinataire,
    this.courseActive,
    this.dernierControle,
  });

  bool get aUneCourse => courseActive != null;
  bool get estRejetee => status == 'rejetee';
  bool get estPubliee => status == 'publiee';

  /// Contestation possible : demande rejetée, pas encore contestée.
  bool get peutContester => estRejetee && dernierControle?['contestation'] == null;

  factory Shipment.fromJson(Map<String, dynamic> json) {
    Map<String, dynamic>? mapOuNull(dynamic v) => v is Map ? Map<String, dynamic>.from(v) : null;
    return Shipment(
      id: json['id'].toString(),
      origin: json['origine'],
      destination: json['destination'],
      description: json['description'],
      weightKg: (json['poids_estime_kg'] as num).toDouble(),
      montantPropose: (json['montant_propose'] as num?)?.toDouble() ?? 0,
      preferredDate: DateTime.parse(json['date_souhaitee']),
      status: json['statut'],
      videoUrl: (json['video_url'] as String?) ?? '',
      telephoneDestinataire: (json['telephone_destinataire'] as String?) ?? '',
      destinataire: mapOuNull(json['destinataire']),
      courseActive: mapOuNull(json['course_active']),
      dernierControle: mapOuNull(json['dernier_controle']),
      createdAt: DateTime.parse(json['date_creation']),
    );
  }
}

class MatchingResult {
  final List<MatchingItem> items;

  MatchingResult({required this.items});

  factory MatchingResult.fromJson(List<dynamic> json) {
    return MatchingResult(
      items: json.map((e) => MatchingItem.fromJson(e)).toList(),
    );
  }
}

/// Une ligne de matching : un trajet (vu par le client) ou une demande
/// (vue par le transporteur).
class MatchingItem {
  final String id;
  final String origin;
  final String destination;
  final DateTime departureDate;
  final double availableCapacityKg;
  final double score;
  final TransporterInfo transporter;
  final String? typeVehicule;
  final DateTime? preferredDate;
  final double? weightKg;
  final double? montantPropose;
  final String? description;
  final Map<String, dynamic>? detailsVisuels;

  MatchingItem({
    required this.id,
    required this.origin,
    required this.destination,
    required this.departureDate,
    required this.availableCapacityKg,
    required this.score,
    required this.transporter,
    this.typeVehicule,
    this.preferredDate,
    this.weightKg,
    this.montantPropose,
    this.description,
    this.detailsVisuels,
  });

  factory MatchingItem.fromJson(Map<String, dynamic> json) {
    final trajet = json['trajet'];
    final demande = json['demande'];
    final score = (json['score'] as num?)?.toDouble() ?? 0.0;

    if (trajet != null) {
      return MatchingItem(
        id: trajet['id'].toString(),
        origin: trajet['origine'],
        destination: trajet['destination'],
        departureDate: DateTime.parse(trajet['date_depart']),
        availableCapacityKg: (trajet['capacite_disponible_kg'] as num).toDouble(),
        score: score,
        transporter: TransporterInfo.fromJson(trajet['transporteur']),
        typeVehicule: trajet['type_vehicule'] as String?,
      );
    }

    final dateSouhaitee = DateTime.parse(demande['date_souhaitee']);
    return MatchingItem(
      id: demande['id'].toString(),
      origin: demande['origine'],
      destination: demande['destination'],
      departureDate: dateSouhaitee,
      availableCapacityKg: (demande['poids_estime_kg'] as num).toDouble(),
      score: score,
      transporter: TransporterInfo.vide(),
      preferredDate: dateSouhaitee,
      weightKg: (demande['poids_estime_kg'] as num?)?.toDouble(),
      montantPropose: (demande['montant_propose'] as num?)?.toDouble(),
      description: demande['description'] as String?,
      detailsVisuels: demande['details_visuels'] is Map
          ? Map<String, dynamic>.from(demande['details_visuels'])
          : null,
    );
  }
}

class TransporterInfo {
  final String id;
  final String nom;
  final String prenom;
  final String telephone;
  final double scoreFiabilite;

  TransporterInfo({
    required this.id,
    required this.nom,
    required this.prenom,
    required this.telephone,
    required this.scoreFiabilite,
  });

  factory TransporterInfo.vide() =>
      TransporterInfo(id: '', nom: '', prenom: '', telephone: '', scoreFiabilite: 0);

  factory TransporterInfo.fromJson(Map<String, dynamic> json) {
    return TransporterInfo(
      id: json['id'].toString(),
      nom: json['nom'] ?? '',
      prenom: json['prenom'] ?? '',
      telephone: json['telephone'] ?? '',
      scoreFiabilite: (json['score_fiabilite'] as num?)?.toDouble() ?? 0,
    );
  }
}
