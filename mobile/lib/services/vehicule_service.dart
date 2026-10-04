import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/auth_service.dart';

final vehiculeServiceProvider = Provider<VehiculeService>((ref) {
  return VehiculeService(ref.read(authServiceProvider));
});

/// Déclarer un véhicule est l'action "devenir transporteur" (BF-22) : le
/// serveur active automatiquement `est_transporteur` sur le compte à cette
/// occasion (cf. vehicule/views.py côté backend).
class VehiculeService {
  final AuthService _authService;

  VehiculeService(this._authService);

  Dio get _dio => _authService.dio;

  Future<Map<String, dynamic>> declarerVehicule({
    required String typeVehicule,
    required String marque,
    required String modele,
    required String immatriculation,
    required double capaciteMaxKg,
  }) async {
    final response = await _dio.post('/vehicules/', data: {
      'type_vehicule': typeVehicule,
      'marque': marque,
      'modele': modele,
      'immatriculation': immatriculation,
      'capacite_max_kg': capaciteMaxKg,
    });
    return response.data;
  }

  /// Retourne le véhicule déjà déclaré par l'utilisateur, ou `null` s'il n'en
  /// a pas encore déclaré (le rôle Transporteur n'est alors pas actif).
  Future<Map<String, dynamic>?> getMonVehicule() async {
    final response = await _dio.get('/vehicules/');
    final results = response.data as List;
    if (results.isEmpty) return null;
    return results.first;
  }
}
