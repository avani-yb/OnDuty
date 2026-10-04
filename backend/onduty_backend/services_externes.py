"""Erreurs communes aux intégrations d'API tierces (Vision, Groq, Smile Identity).

Chaque fournisseur est isolé dans son propre module (BNF-16) et traduit ses
erreurs techniques (réseau, timeout, quota, réponse illisible) en l'une des
exceptions ci-dessous. Les vues n'ont ainsi qu'un seul type d'erreur à gérer
pour informer clairement l'utilisateur (BNF-03 / BNF-10), sans dépendre du SDK
de chaque fournisseur.
"""


class ServiceExterneErreur(Exception):
    """Erreur générique d'un service tiers.

    `message_utilisateur` est le texte affichable dans l'application ; le
    message technique (`str(exc)`) reste réservé aux journaux.
    """

    message_utilisateur = (
        "Un service de vérification est momentanément indisponible. "
        "Réessayez dans quelques instants."
    )

    def __init__(self, service, detail=""):
        self.service = service
        self.detail = detail
        super().__init__(f"[{service}] {detail}")


class ServiceNonConfigure(ServiceExterneErreur):
    """Clé ou paramètre manquant dans le .env."""


class ServiceIndisponible(ServiceExterneErreur):
    """Erreur réseau, erreur 5xx ou quota dépassé côté fournisseur."""


class ServiceSature(ServiceIndisponible):
    """Limite de débit ou quota du fournisseur atteint (HTTP 429)."""

    message_utilisateur = (
        "Le service de vérification est très sollicité en ce moment. "
        "Réessayez dans une minute."
    )


class ServiceTimeout(ServiceExterneErreur):
    """Le fournisseur n'a pas répondu dans le délai imparti."""


class ReponseInvalide(ServiceExterneErreur):
    """Réponse reçue mais inexploitable (format inattendu, JSON invalide)."""
