import 'package:dio/dio.dart';

/// Traduit une erreur technique (le plus souvent une [DioException] renvoyée
/// par l'API) en un message clair et actionnable pour l'utilisateur, en
/// français. À utiliser partout où une erreur réseau/API est affichée dans
/// l'interface, au lieu de `e.toString()` qui expose des détails techniques
/// (DioException, code Socket, etc.) sans intérêt pour l'utilisateur.
///
/// [unauthorizedMessage] permet de personnaliser le message pour un 401
/// précis (ex. "Numéro ou mot de passe incorrect" sur l'écran de connexion),
/// sinon un message générique de session expirée est utilisé.
String friendlyError(Object error, {String? unauthorizedMessage}) {
  if (error is! DioException) {
    print("The fucking mistake $error");
    return "Une erreur est survenue. Réessayez.";
  }

  switch (error.type) {
    case DioExceptionType.connectionError:
      print("Erreur de connexion");
    case DioExceptionType.connectionTimeout:
      print("Connexion expiree");
    case DioExceptionType.sendTimeout:
      print("Expedition de paquet echec");
    case DioExceptionType.receiveTimeout:
      print("Recepteur echec");
      return "Impossible de contacter le serveur. Vérifiez votre connexion et réessayez.";
    default:
      break;
  }

  final statusCode = error.response?.statusCode;
  final data = error.response?.data;

  // DRF renvoie souvent {"detail": "..."} ou un dict d'erreurs par champ
  // (ex. {"telephone": ["Ce champ est obligatoire."]}).
  String? serverMessage;
  if (data is Map) {
    final detail = data['detail'];
    if (detail is String && detail.isNotEmpty) {
      serverMessage = detail;
    } else {
      for (final value in data.values) {
        if (value is List && value.isNotEmpty) {
          serverMessage = value.first.toString();
          break;
        }
        if (value is String && value.isNotEmpty) {
          serverMessage = value;
          break;
        }
      }
    }
  }

  switch (statusCode) {
    case 400:
      return serverMessage ?? "Certaines informations sont invalides.";
    case 401:
      return unauthorizedMessage ?? "Session expirée, merci de vous reconnecter.";
    case 403:
      return serverMessage ?? "Vous n'avez pas accès à cette fonctionnalité.";
    case 404:
      return "Élément introuvable.";
    case 409:
      return serverMessage ?? "Cette action n'est pas possible pour le moment.";
    case 503:
      return serverMessage ?? "Le serveur rencontre un problème. Réessayez plus tard.";
    case 500:
    case 502:
      return "Le serveur rencontre un problème. Réessayez plus tard.";
    default:
      print("Fucking mistake $statusCode");
      return serverMessage ?? "Une erreur est survenue. Réessayez.";
  }
}
