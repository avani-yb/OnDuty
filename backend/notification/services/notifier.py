"""Point d'entrée unique pour notifier un utilisateur depuis la logique métier.

Une notification ne doit jamais faire échouer l'action qui la déclenche
(paiement, changement de statut...) : toute erreur est journalisée et ignorée.
"""

import logging

logger = logging.getLogger(__name__)


def notifier(utilisateur, type_notification, titre, corps, **data):
    """Enregistre et envoie une notification ; ne lève jamais d'exception."""
    if utilisateur is None:
        return
    try:
        from .fcm import envoyer_notification_utilisateur

        envoyer_notification_utilisateur(utilisateur, type_notification, titre, corps, data)
    except Exception:
        logger.exception("Notification non envoyée à l'utilisateur %s : %s", getattr(utilisateur, "pk", None), titre)
