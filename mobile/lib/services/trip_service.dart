import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/auth_service.dart';

final tripServiceProvider = Provider<TripService>((ref) {
  return TripService(ref.read(authServiceProvider));
});

class TripService {
  final AuthService _authService;

  TripService(this._authService);

  Dio get _dio => _authService.dio;

  Future<Trip> createTrip({
    required String origin,
    required String destination,
    required DateTime departureDate,
    required double capacityKg,
  }) async {
    final response = await _dio.post('/trajets/', data: {
      'origine': origin,
      'destination': destination,
      'date_depart': departureDate.toIso8601String(),
      'capacite_disponible_kg': capacityKg,
    });

    return Trip.fromJson(response.data);
  }

  /// Trajets du transporteur, déjà triés par le serveur : actifs, en cours, passés.
  Future<List<Trip>> getMyTrips() async {
    final response = await _dio.get('/trajets/');
    return (response.data as List).map((e) => Trip.fromJson(e)).toList();
  }

  Future<Trip> getTrip(String id) async {
    final response = await _dio.get('/trajets/$id/');
    return Trip.fromJson(response.data);
  }

  /// Modification d'un trajet actif. Avec des courses, seule la capacité
  /// est acceptée par le serveur (jamais sous les kg déjà réservés).
  Future<Trip> updateTrip(String id, Map<String, dynamic> champs) async {
    final response = await _dio.patch('/trajets/$id/', data: champs);
    return Trip.fromJson(response.data);
  }

  /// Supprime le trajet ; retourne le nombre de courses annulées.
  Future<int> deleteTrip(String id) async {
    final response = await _dio.delete('/trajets/$id/');
    final data = response.data;
    return data is Map ? (data['courses_annulees'] as int? ?? 0) : 0;
  }
}

class Trip {
  final String id;
  final String origin;
  final String destination;
  final DateTime departureDate;
  final double capacityKg;
  final String status;

  /// 'actif' (date à venir), 'en_cours' (aujourd'hui) ou 'passe'.
  final String etat;
  final bool estModifiable;
  final double kgReserves;
  final double capaciteRestanteKg;
  final bool aDesCourses;
  final String? typeVehicule;
  final DateTime createdAt;
  final String? transporteurId;
  final List<dynamic>? courses;

  Trip({
    required this.id,
    required this.origin,
    required this.destination,
    required this.departureDate,
    required this.capacityKg,
    required this.status,
    required this.etat,
    required this.estModifiable,
    required this.kgReserves,
    required this.capaciteRestanteKg,
    required this.aDesCourses,
    required this.createdAt,
    this.typeVehicule,
    this.transporteurId,
    this.courses,
  });

  factory Trip.fromJson(Map<String, dynamic> json) {
    double nombre(dynamic v) => (v as num?)?.toDouble() ?? 0;
    return Trip(
      id: json['id'].toString(),
      origin: json['origine'],
      destination: json['destination'],
      departureDate: DateTime.parse(json['date_depart']),
      capacityKg: nombre(json['capacite_disponible_kg']),
      status: json['statut'],
      etat: (json['etat'] as String?) ?? json['statut'],
      estModifiable: json['est_modifiable'] == true,
      kgReserves: nombre(json['kg_reserves']),
      capaciteRestanteKg: nombre(json['capacite_restante_kg']),
      aDesCourses: json['a_des_courses'] == true,
      typeVehicule: json['type_vehicule'] as String?,
      createdAt: DateTime.parse(json['date_creation']),
      // Le backend renvoie l'id brut du transporteur (entier), pas un objet imbriqué.
      transporteurId: json['transporteur']?.toString(),
      courses: json['courses'] as List<dynamic>?,
    );
  }
}
