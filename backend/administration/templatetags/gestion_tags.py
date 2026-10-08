"""Filtres d'affichage du site /gestion/ (couleurs de statut, montants)."""

from django import template

register = template.Library()

COULEURS = {
    # Courses
    "livree": "vert", "annulee": "gris", "en_litige": "rouge",
    "reservee": "orange", "proposition_montant": "orange", "en_attente_paiement": "orange",
    "payee": "brun", "depart": "brun", "en_route": "brun", "arrivee": "brun",
    # Litiges
    "ouvert": "rouge", "en_cours_analyse": "orange", "resolu": "vert",
    # Paiements et versements
    "en_attente": "orange", "echoue": "rouge", "bloque_escrow": "brun",
    "libere": "vert", "rembourse": "gris", "en_cours": "orange", "effectue": "vert",
    # Comptes et contrôles IA
    "actif": "vert", "suspendu": "rouge", "valide": "vert", "rejete": "rouge",
    "validee": "vert", "rejetee": "rouge", "a_revoir": "orange",
}


@register.filter
def couleur(statut):
    """Classe CSS de pastille pour un statut."""
    return COULEURS.get(str(statut), "gris")


@register.filter
def fcfa(montant):
    """12500 → « 12 500 FCFA »."""
    if montant in (None, ""):
        return "—"
    return f"{int(round(float(montant))):,}".replace(",", " ") + " FCFA"
