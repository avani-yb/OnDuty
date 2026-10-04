"""Service d'envoi de notifications push via Firebase Cloud Messaging.

En production : utilise firebase-admin SDK.
En développement : simule l'envoi (mock).
"""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class FCMService:
    """Service d'envoi de notifications via FCM."""

    def __init__(self):
        self._app = None
        self._initialized = False

    def _init_firebase(self):
        """Initialise Firebase Admin SDK si les credentials sont disponibles."""
        if self._initialized:
            return

        try:
            import firebase_admin
            from firebase_admin import credentials

            # Chercher le fichier de credentials
            cred_path = getattr(settings, "FIREBASE_CREDENTIALS_PATH", None)
            if cred_path:
                cred = credentials.Certificate(cred_path)
                firebase_admin.initialize_app(cred)
                self._initialized = True
                logger.info("Firebase Admin SDK initialisé")
            else:
                logger.warning("FIREBASE_CREDENTIALS_PATH non configuré - mode simulation")
        except ImportError:
            logger.warning("firebase-admin non installé - mode simulation")
        except Exception as e:
            logger.error(f"Erreur initialisation Firebase: {e}")

    def envoyer_notification(self, token: str, titre: str, corps: str, data: dict = None):
        """Envoie une notification à un token FCM unique.

        Retourne (success: bool, message_id: str | None, error: str | None)
        """
        if not self._initialized:
            self._init_firebase()

        if not self._initialized:
            # Mode simulation
            logger.info(f"[SIMULATION FCM] → {token[:20]}... | {titre}: {corps}")
            return True, "simulated-message-id", None

        try:
            from firebase_admin import messaging

            message = messaging.Message(
                notification=messaging.Notification(title=titre, body=corps),
                data=data or {},
                token=token,
            )
            response = messaging.send(message)
            logger.info(f"Notification FCM envoyée: {response}")
            return True, response, None
        except Exception as e:
            logger.error(f"Erreur envoi FCM: {e}")
            return False, None, str(e)

    def envoyer_multicast(self, tokens: list, titre: str, corps: str, data: dict = None):
        """Envoie une notification à plusieurs tokens (multicast).

        Retourne (success_count: int, failure_count: int, results: list)
        """
        if not self._initialized:
            self._init_firebase()

        if not self._initialized:
            # Mode simulation
            logger.info(f"[SIMULATION FCM MULTICAST] → {len(tokens)} tokens | {titre}: {corps}")
            return len(tokens), 0, [{"success": True, "message_id": f"sim-{i}"} for i in range(len(tokens))]

        try:
            from firebase_admin import messaging

            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=titre, body=corps),
                data=data or {},
                tokens=tokens,
            )
            response = messaging.send_multicast(message)
            logger.info(f"Multicast FCM: {response.success_count} succès, {response.failure_count} échecs")
            return response.success_count, response.failure_count, response.responses
        except Exception as e:
            logger.error(f"Erreur multicast FCM: {e}")
            return 0, len(tokens), [{"success": False, "error": str(e)}] * len(tokens)


# Instance singleton
fcm_service = FCMService()


def envoyer_notification_utilisateur(utilisateur, type_notification, titre, corps, data=None):
    """Enregistre une notification pour l'utilisateur et l'envoie en push.

    La notification est TOUJOURS enregistrée en base : elle apparaît dans la
    liste de l'application même sans push (Firebase non configuré, aucun
    appareil enregistré). Le push est envoyé à tous les tokens actifs.

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

    tokens = list(
        FCMToken.objects.filter(utilisateur=utilisateur, actif=True).values_list("token", flat=True)
    )
    if not tokens:
        return 0, 0

    success_count = 0
    dernier_id = None
    for token in tokens:
        success, msg_id, error = fcm_service.envoyer_notification(token, titre, corps, data)
        if success:
            success_count += 1
            dernier_id = msg_id
        else:
            logger.error(f"Échec envoi notification {notification.id}: {error}")

    if success_count:
        notification.marquer_envoyee(dernier_id)
    else:
        notification.marquer_echec()
    return success_count, len(tokens) - success_count
