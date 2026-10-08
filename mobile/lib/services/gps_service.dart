import 'dart:async';
import 'dart:ui';

import 'package:flutter/foundation.dart';
import 'package:flutter_background_service/flutter_background_service.dart';
import 'package:geolocator/geolocator.dart';

import 'auth_service.dart';
import 'push_service.dart';

/// Suivi GPS du transporteur pendant ses courses (du départ à la livraison).
///
/// Un service Android au premier plan (notification permanente « OnDuty
/// partage votre position ») envoie la position au serveur toutes les
/// 45 secondes, même application fermée. Il s'arrête tout seul quand le
/// serveur indique qu'aucune course n'est plus en cours de transport.
class GpsService {
  GpsService._();

  static const _intervalle = Duration(seconds: 45);
  static final _service = FlutterBackgroundService();

  /// À appeler au démarrage de l'application (après PushService.initialiser,
  /// qui crée le canal de la notification permanente).
  static Future<void> configurer() async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return;
    await _service.configure(
      androidConfiguration: AndroidConfiguration(
        onStart: _demarrer,
        autoStart: false,
        autoStartOnBoot: false,
        isForegroundMode: true,
        notificationChannelId: PushService.canalGps.id,
        initialNotificationTitle: 'OnDuty',
        initialNotificationContent: 'Partage de votre position pour la course en cours',
        foregroundServiceNotificationId: 7001,
        foregroundServiceTypes: [AndroidForegroundType.location],
      ),
      iosConfiguration: IosConfiguration(autoStart: false, onForeground: _demarrer),
    );
  }

  /// Permissions de localisation : « pendant l'utilisation » puis « toujours ».
  /// Retourne true si le suivi en arrière-plan est autorisé.
  static Future<bool> permissionArrierePlan() async {
    if (!await Geolocator.isLocationServiceEnabled()) return false;
    var permission = await Geolocator.checkPermission();
    if (permission == LocationPermission.denied) {
      permission = await Geolocator.requestPermission();
    }
    if (permission == LocationPermission.whileInUse) {
      // Deuxième demande : Android propose « Toujours autoriser ».
      permission = await Geolocator.requestPermission();
    }
    return permission == LocationPermission.always;
  }

  static Future<bool> permissionAccordee() async {
    final permission = await Geolocator.checkPermission();
    return permission == LocationPermission.always || permission == LocationPermission.whileInUse;
  }

  /// Démarre le service si le serveur indique une course en cours de transport.
  static Future<void> demarrerSiNecessaire(AuthService auth) async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return;
    try {
      final reponse = await auth.dio.get('/positions/');
      if (reponse.data['suivi_actif'] == true && await permissionAccordee()) {
        await demarrer();
      }
    } catch (e) {
      debugPrint('Vérification du suivi GPS impossible : $e');
    }
  }

  static Future<void> demarrer() async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return;
    if (!await _service.isRunning()) await _service.startService();
  }

  static Future<void> arreter() async {
    if (kIsWeb || defaultTargetPlatform != TargetPlatform.android) return;
    if (await _service.isRunning()) _service.invoke('arreter');
  }

  /// Point d'entrée du service (isolate séparé, sans interface).
  @pragma('vm:entry-point')
  static Future<void> _demarrer(ServiceInstance service) async {
    DartPluginRegistrant.ensureInitialized();
    final auth = AuthService();
    Timer? minuteur;

    service.on('arreter').listen((_) {
      minuteur?.cancel();
      service.stopSelf();
    });

    Future<void> envoyer() async {
      try {
        final position = await Geolocator.getCurrentPosition(
          locationSettings: const LocationSettings(
            accuracy: LocationAccuracy.high,
            timeLimit: Duration(seconds: 30),
          ),
        );
        final reponse = await auth.dio.post('/positions/', data: {
          'latitude': double.parse(position.latitude.toStringAsFixed(6)),
          'longitude': double.parse(position.longitude.toStringAsFixed(6)),
          'precision': position.accuracy,
        });
        if (reponse.data['suivi_actif'] != true) {
          // Plus aucune course en transport : on libère le GPS et la batterie.
          minuteur?.cancel();
          service.stopSelf();
        }
      } catch (e) {
        // GPS indisponible ou pas de réseau : on réessaiera au prochain passage.
        debugPrint('Envoi de position impossible : $e');
      }
    }

    await envoyer();
    minuteur = Timer.periodic(_intervalle, (_) => envoyer());
  }
}
