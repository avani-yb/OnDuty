"""Envoi des notifications push via Firebase Cloud Messaging (FCM).

Configuration : FIREBASE_CREDENTIALS_PATH dans le .env, chemin vers la clé
JSON du compte de service Firebase (à placer dans backend/secrets/, dossier
exclu du dépôt). Sans cette clé, les notifications restent enregistrées et
visibles dans l'application, mais aucun push n'est envoyé (mode simulation).
"""

import logging
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

# Canal Android déclaré par l'application (notifications importantes).
CANAL_ANDROID = "onduty_courses"


class FCMService:
    """Service d'envoi de notifications via FCM."""

    def __init__(self):
        self._initialized = False
        self._tente = False

    def _init_firebase(self):
        """Initialise Firebase Admin SDK une seule fois, si la clé est configurée."""
        if self._initialized or self._tente:
            return
        self._tente = True
        chemin = getattr(settings, "FIREBASE_CREDENTIALS_PATH", "")
        if not chemin:
            logger.warning("FIREBASE_CREDENTIALS_PATH non configuré : push désactivé (simulation)")
            return
        chemin = Path(chemin)
        if not chemin.is_absolute():
            chemin = Path(settings.BASE_DIR) / chemin
        try:
            import firebase_admin
            from firebase_admin import credentials

            if not firebase_admin._apps:
                firebase_admin.initialize_app(credentials.Certificate(str(chemin)))
            self._initialized = True
            logger.info("Firebase Admin SDK initialisé")
        except ImportError:
            logger.warning("firebase-admin non installé : push désactivé (simulation)")
        except Exception as e:
            logger.error(f"Erreur d'initialisation Firebase ({chemin}) : {e}")

    @staticmethod
    def _message(token, titre, corps, data):
        from firebase_admin import messaging

        return messaging.Message(
            notification=messaging.Notification(title=titre, body=corps),
            data={k: str(v) for k, v in (data or {}).items()},
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(channel_id=CANAL_ANDROID),
            ),
            token=token,
        )

    def envoyer_notification(self, token: str, titre: str, corps: str, data: dict = None):
        """Envoie une notification à un token FCM unique.

        Retourne (succès, message_id, erreur, token_invalide).
        """
        self._init_firebase()
        if not self._initialized:
            logger.info(f"[SIMULATION FCM] → {token[:20]}... | {titre}: {corps}")
            return True, "simulated-message-id", None, False

        from firebase_admin import messaging

        try:
            reponse = messaging.send(self._message(token, titre, corps, data))
            return True, reponse, None, False
        except (messaging.UnregisteredError, messaging.SenderIdMismatchError) as e:
            # Application désinstallée ou token d'un autre projet : à désactiver.
            return False, None, str(e), True
        except Exception as e:
            logger.error(f"Erreur envoi FCM : {e}")
            return False, None, str(e), False


fcm_service = FCMService()


def envoyer_notification_utilisateur(utilisateur, type_notification, titre, corps, data=None):
    """Enregistre une notification pour l'utilisateur et l'envoie en push.

    La notification est TOUJOURS enregistrée en base : elle apparaît dans la
    liste de l'application même sans push. Le push est envoyé à tous les
    appareils actifs de l'utilisateur ; les tokens périmés sont désactivés.

    Retourne (nb_envois_reussis, nb_echecs).
    """
    from ..models import FCMToken, Notification

    data = {k: str(v) for k, v in (data or {}).items()}
    notification = Notification.objects.create(
        utilisateur=utilisateur,
        type_notification=type_notification,
        titre=titre,
        corps=corps,
        data=data,
    )

    tokens = list(FCMToken.objects.filter(utilisateur=utilisateur, actif=True))
    if not tokens:
        return 0, 0

    data_push = {**data, "notification_id": str(notification.pk), "type": type_notification}
    succes = 0
    dernier_id = None
    for fcm_token in tokens:
        ok, msg_id, erreur, invalide = fcm_service.envoyer_notification(fcm_token.token, titre, corps, data_push)
        if ok:
            succes += 1
            dernier_id = msg_id
        else:
            logger.error(f"Échec envoi notification {notification.id} : {erreur}")
            if invalide:
                fcm_token.actif = False
                fcm_token.save(update_fields=["actif"])

    if succes:
        notification.marquer_envoyee(dernier_id)
    else:
        notification.marquer_echec()
    return succes, len(tokens) - succes
