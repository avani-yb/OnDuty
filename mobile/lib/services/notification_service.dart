import 'package:dio/dio.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../services/auth_service.dart';

final notificationServiceProvider = Provider<NotificationService>((ref) {
  return NotificationService(ref.read(authServiceProvider));
});

/// Notifications enregistrées par le serveur (liste derrière la cloche).
/// Le push Firebase viendra s'ajouter quand le projet Firebase existera.
class NotificationService {
  final AuthService _authService;

  NotificationService(this._authService);

  Dio get _dio => _authService.dio;

  Future<List<AppNotification>> getNotifications() async {
    final response = await _dio.get('/notifications/');
    return (response.data as List).map((e) => AppNotification.fromJson(e)).toList();
  }

  Future<int> getNombreNonLues() async {
    final response = await _dio.get('/notifications/compteur/');
    return (response.data['non_lues'] as int?) ?? 0;
  }

  Future<void> marquerLue(String id) async {
    await _dio.post('/notifications/$id/marquer_lue/');
  }

  Future<void> toutMarquerLu() async {
    await _dio.post('/notifications/tout_marquer_lu/');
  }
}

class AppNotification {
  final String id;
  final String type;
  final String titre;
  final String corps;
  final Map<String, dynamic> data;
  final bool lue;
  final DateTime? date;

  AppNotification({
    required this.id,
    required this.type,
    required this.titre,
    required this.corps,
    required this.data,
    required this.lue,
    this.date,
  });

  String? get courseId => data['course_id']?.toString();
  String? get demandeId => data['demande_id']?.toString();
  String? get trajetId => data['trajet_id']?.toString();

  factory AppNotification.fromJson(Map<String, dynamic> json) {
    return AppNotification(
      id: json['id'].toString(),
      type: (json['type_notification'] as String?) ?? '',
      titre: (json['titre'] as String?) ?? '',
      corps: (json['corps'] as String?) ?? '',
      data: Map<String, dynamic>.from(json['data'] ?? {}),
      lue: json['lue'] == true,
      date: json['date_creation'] != null ? DateTime.tryParse(json['date_creation']) : null,
    );
  }
}
