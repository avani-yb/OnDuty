import 'dart:convert';
import 'dart:io';

import 'package:dio/dio.dart';
import 'package:dio/io.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

final authServiceProvider = Provider<AuthService>((ref) {
  return AuthService();
});

class AuthService {
  // URL configurable au build : `flutter build apk --dart-define=API_BASE_URL=https://mon-domaine.tld/api`.
  // En l'absence de valeur fournie, on retombe sur le serveur de dev local.
  static const _baseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://127.0.0.1:8000/api',
  );
  static const _accessTokenKey = 'access_token';
  static const _refreshTokenKey = 'refresh_token';
  static const _userIdKey = 'user_id';
  static const _userKey = 'user_data';

  final Dio _dio = Dio(BaseOptions(
    baseUrl: _baseUrl,
    connectTimeout: const Duration(seconds: 30),
    receiveTimeout: const Duration(seconds: 30),
    headers: {
      'Content-Type': 'application/json',
      // Le serveur de développement Django (`runserver`) gère mal les
      // connexions HTTP persistantes (keep-alive) que dart:io essaie
      // d'établir par défaut, ce qui provoque des erreurs aléatoires
      // "Connection reset by peer" côté client. On force une connexion
      // fraîche à chaque requête pour l'éviter (léger surcoût réseau,
      // sans impact perceptible en usage normal).
      'Connection': 'close',
    },
  ));
  final FlutterSecureStorage _storage = const FlutterSecureStorage();

  Dio get dio => _dio;

  /// URL racine du serveur (sans le suffixe `/api`), pour construire l'URL
  /// absolue d'un fichier média dont l'API ne renvoie qu'un chemin relatif
  /// (ex. `/media/photos_profil/x.jpg`).
  static String get serverRootUrl => _baseUrl.replaceAll(RegExp(r'/api/?$'), '');

  /// Construit une URL absolue à partir d'un chemin renvoyé par l'API,
  /// qu'il soit déjà absolu (http...) ou relatif (/media/...).
  static String? absoluteMediaUrl(String? path) {
    if (path == null || path.isEmpty) return null;
    if (path.startsWith('http://') || path.startsWith('https://')) return path;
    return '$serverRootUrl$path';
  }

  AuthService() {
    // Empêche dart:io de réutiliser (pooling) une connexion HTTP déjà
    // ouverte : combiné à l'en-tête `Connection: close` ci-dessus, ça
    // élimine les erreurs "Connection reset by peer" observées avec le
    // serveur de développement Django, qui ne gère pas bien le keep-alive.
    (_dio.httpClientAdapter as IOHttpClientAdapter).createHttpClient = () {
      final client = HttpClient();
      client.idleTimeout = Duration.zero;
      return client;
    };

    _dio.interceptors.add(InterceptorsWrapper(
      onRequest: (options, handler) async {
        final token = await _storage.read(key: _accessTokenKey);
        if (token != null) {
          options.headers['Authorization'] = 'Bearer $token';
        }
        return handler.next(options);
      },
      onError: (DioException error, ErrorInterceptorHandler handler) async {
        if (error.response?.statusCode == 401) {
          final refreshed = await _refreshToken();
          if (refreshed) {
            final token = await _storage.read(key: _accessTokenKey);
            if (token != null) {
              error.requestOptions.headers['Authorization'] = 'Bearer $token';
              return handler.resolve(await _dio.fetch(error.requestOptions));
            }
          }
        }
        return handler.next(error);
      },
    ));
  }

  /// Décode le payload d'un JWT (sans vérifier la signature : ce n'est pas
  /// nécessaire côté client, le token vient d'un canal HTTPS de confiance et
  /// est de toute façon vérifié par le serveur à chaque requête).
  Map<String, dynamic> _decodeJwtPayload(String token) {
    final parts = token.split('.');
    if (parts.length != 3) return {};
    var payload = parts[1];
    payload = base64Url.normalize(payload);
    final decoded = utf8.decode(base64Url.decode(payload));
    return jsonDecode(decoded) as Map<String, dynamic>;
  }

  Future<void> _storeTokens(String access, String refresh) async {
    await _storage.write(key: _accessTokenKey, value: access);
    await _storage.write(key: _refreshTokenKey, value: refresh);

    final payload = _decodeJwtPayload(access);
    final userId = payload['user_id']?.toString();
    if (userId != null) {
      await _storage.write(key: _userIdKey, value: userId);
    }
  }

  Future<void> login({required String phone, required String password}) async {
    final response = await _dio.post('/token/', data: {
      'telephone': phone,
      'password': password,
    });

    final access = response.data['access'] as String;
    final refresh = response.data['refresh'] as String;
    await _storeTokens(access, refresh);
  }

  Future<void> register({
    required String telephone,
    required String password,
    required String nom,
    required String prenom,
    String? email,
  }) async {
    await _dio.post('/inscription/', data: {
      'telephone': telephone,
      'password': password,
      'nom': nom,
      'prenom': prenom,
      if (email != null) 'email': email,
    });
    await login(phone: telephone, password: password);
  }

  Future<void> logout() async {
    await _storage.delete(key: _accessTokenKey);
    await _storage.delete(key: _refreshTokenKey);
    await _storage.delete(key: _userIdKey);
    await _storage.delete(key: _userKey);
  }

  Future<bool> _refreshToken() async {
    try {
      final refresh = await _storage.read(key: _refreshTokenKey);
      if (refresh == null) return false;

      final response = await _dio.post('/token/refresh/', data: {'refresh': refresh});
      final access = response.data['access'] as String;
      await _storage.write(key: _accessTokenKey, value: access);
      // Le serveur fait tourner les jetons de rafraîchissement : on garde le nouveau.
      final nouveauRefresh = response.data['refresh'] as String?;
      if (nouveauRefresh != null) await _storage.write(key: _refreshTokenKey, value: nouveauRefresh);
      return true;
    } catch (_) {
      return false;
    }
  }

  Future<String?> getAccessToken() async {
    return _storage.read(key: _accessTokenKey);
  }

  /// Identifiant de l'utilisateur connecté (extrait du JWT à la connexion).
  /// Nécessaire pour appeler `/api/profil/<id>/`, qui n'a pas de raccourci "moi-même".
  Future<String?> getUserId() async {
    return _storage.read(key: _userIdKey);
  }

  Future<bool> isLoggedIn() async {
    final token = await _storage.read(key: _accessTokenKey);
    return token != null;
  }

  Future<void> requestPasswordReset({required String phone}) async {
    await _dio.post('/password/reset/request/', data: {
      'telephone': phone,
    });
  }

  Future<void> resetPassword({
    required String phone,
    required String code,
    required String newPassword,
  }) async {
    await _dio.post('/password/reset/confirm/', data: {
      'telephone': phone,
      'code': code,
      'new_password': newPassword,
    });
  }
}