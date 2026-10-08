import 'dart:convert';

import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

import 'auth_service.dart';

/// Notifications push (Firebase Cloud Messaging).
///
/// Sans `google-services.json` (projet Firebase non créé), Firebase ne
/// s'initialise pas : l'application fonctionne normalement et les
/// notifications restent consultables derrière la cloche de l'accueil.
class PushService {
  PushService._();

  /// Canal des notifications de course (même identifiant que côté serveur).
  static const canalCourses = AndroidNotificationChannel(
    'onduty_courses',
    'Courses et paiements',
    description: 'Réservations, paiements, suivi des colis, incidents.',
    importance: Importance.high,
  );

  /// Canal de la notification permanente du suivi GPS (discrète).
  static const canalGps = AndroidNotificationChannel(
    'onduty_gps',
    'Partage de position',
    description: 'Affichée pendant que votre position est partagée pour une course.',
    importance: Importance.low,
  );

  static final _locales = FlutterLocalNotificationsPlugin();
  static bool _firebaseDisponible = false;
  static bool _initialise = false;

  /// Ouvre une route de l'application (branché sur le routeur par l'app).
  static void Function(String route)? ouvrirRoute;

  static bool get disponible => _firebaseDisponible;

  /// À appeler au démarrage, avant runApp.
  static Future<void> initialiser() async {
    if (_initialise) return;
    _initialise = true;

    await _locales.initialize(
      settings: const InitializationSettings(
        android: AndroidInitializationSettings('@mipmap/ic_launcher'),
        iOS: DarwinInitializationSettings(),
      ),
      onDidReceiveNotificationResponse: (reponse) => _ouvrirDepuisPayload(reponse.payload),
    );
    final android = _locales.resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>();
    await android?.createNotificationChannel(canalCourses);
    await android?.createNotificationChannel(canalGps);

    try {
      await Firebase.initializeApp();
      _firebaseDisponible = true;
    } catch (e) {
      debugPrint('Firebase non configuré (google-services.json absent) : push désactivé. $e');
      return;
    }

    // Application ouverte : Android n'affiche pas la notification, on la
    // montre nous-mêmes.
    FirebaseMessaging.onMessage.listen((message) {
      final notification = message.notification;
      if (notification == null) return;
      _locales.show(
        id: message.hashCode,
        title: notification.title,
        body: notification.body,
        notificationDetails: NotificationDetails(
          android: AndroidNotificationDetails(
            canalCourses.id,
            canalCourses.name,
            channelDescription: canalCourses.description,
            importance: Importance.high,
            priority: Priority.high,
          ),
        ),
        payload: jsonEncode(message.data),
      );
    });

    // Notification touchée alors que l'app était en arrière-plan ou fermée.
    FirebaseMessaging.onMessageOpenedApp.listen((message) => _ouvrir(message.data));
    final initiale = await FirebaseMessaging.instance.getInitialMessage();
    if (initiale != null) {
      // Laisse le routeur se construire avant de naviguer.
      Future.delayed(const Duration(milliseconds: 800), () => _ouvrir(initiale.data));
    }
  }

  /// Enregistre ce téléphone auprès du serveur pour recevoir les push.
  static Future<void> enregistrerAppareil(AuthService auth) async {
    if (!_firebaseDisponible) return;
    try {
      final messaging = FirebaseMessaging.instance;
      await messaging.requestPermission();
      final token = await messaging.getToken();
      if (token != null) await _envoyerToken(auth, token);
      messaging.onTokenRefresh.listen((nouveau) => _envoyerToken(auth, nouveau));
    } catch (e) {
      debugPrint('Enregistrement push impossible : $e');
    }
  }

  /// Déconnexion : ce téléphone ne reçoit plus les notifications du compte.
  static Future<void> oublierAppareil(AuthService auth) async {
    if (!_firebaseDisponible) return;
    try {
      final token = await FirebaseMessaging.instance.getToken();
      if (token != null) await auth.dio.post('/fcm-tokens/oublier/', data: {'token': token});
    } catch (_) {
      // Sans réseau : le serveur désactivera le token au prochain échec d'envoi.
    }
  }

  static Future<void> _envoyerToken(AuthService auth, String token) async {
    await auth.dio.post('/fcm-tokens/', data: {
      'token': token,
      'platform': defaultTargetPlatform == TargetPlatform.iOS ? 'ios' : 'android',
    });
  }

  /// Route à ouvrir pour une notification (course, demande ou trajet).
  static String? routePour(Map<String, dynamic> data) {
    if (data['course_id'] != null) return '/shipment/${data['course_id']}';
    if (data['demande_id'] != null) return '/demande/${data['demande_id']}';
    if (data['trajet_id'] != null) return '/trip/${data['trajet_id']}';
    return '/notifications';
  }

  static void _ouvrir(Map<String, dynamic> data) {
    final route = routePour(data);
    if (route != null) ouvrirRoute?.call(route);
  }

  static void _ouvrirDepuisPayload(String? payload) {
    if (payload == null || payload.isEmpty) return;
    try {
      _ouvrir(Map<String, dynamic>.from(jsonDecode(payload) as Map));
    } catch (_) {}
  }
}
