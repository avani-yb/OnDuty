"""Service de matching intelligent.

Croise les demandes publiées (validées par l'IA) avec les trajets actifs des
transporteurs et classe les résultats selon les critères du fichier
`06-fonctionnalites-detaillees.md` (section 3) :

1. Fiabilité du transporteur (poids le plus fort) — `score_fiabilite`
2. Proximité géographique (origine/destination)
3. Compatibilité de date (fenêtre proche)
4. Capacité disponible (filtre d'éligibilité : doit être suffisante)

Le score final est une combinaison pondérée normalisée (0-100) qui respecte
cet ordre de priorité. Une capacité insuffisante ou un itinéraire totalement
incompatible excluent le trajet du résultat.
"""

import unicodedata
from datetime import timedelta

from django.utils import timezone

from demande.models import Demande
from trajet.models import Trajet

# Fenêtre de date retenue pour une compatibilité pleine (jours).
FENETRE_DATE_JOURS = 3

# Pondération des critères (ordre de priorité de la doc 06 §3.1).
PONDERATION = {
    "fiabilite": 0.40,
    "proximite": 0.30,
    "date": 0.20,
    "capacite": 0.10,
}


def normaliser(texte: str) -> str:
    """Normalise une chaîne (minuscules, sans accents) pour la comparaison."""
    chaine = unicodedata.normalize("NFD", texte or "").encode(
        "ascii", "ignore"
    ).decode("ascii")
    return chaine.strip().lower()


def _score_proximite(demande: Demande, trajet: Trajet):
    """Correspondance origine/destination (0 si incompatible, 100 si identique).

    Un trajet pertinent relie les deux mêmes extrémités que la demande.
    """
    orig = normaliser(demande.origine) == normaliser(trajet.origine)
    dest = normaliser(demande.destination) == normaliser(trajet.destination)
    if orig and dest:
        return 100
    # Une seule extrémité identique : proximité partielle (trajet voisin).
    if orig or dest:
        return 50
    return 0


def _score_date(demande: Demande, trajet: Trajet):
    """Compatibilité de date : 100 dans la fenêtre, décroît ensuite."""
    if demande.date_souhaitee and trajet.date_depart:
        ecart_jours = abs((demande.date_souhaitee - trajet.date_depart).days)
    else:
        ecart_jours = 0
    if ecart_jours <= FENETRE_DATE_JOURS:
        return 100
    return max(0, 100 - (ecart_jours - FENETRE_DATE_JOURS) * 15)


def _score_capacite(demande: Demande, trajet: Trajet):
    """Capacité disponible : 100 si largement suffisante, décroît sinon.

    Retourne 0 si la capacité est insuffisante (trajet non éligible).
    """
    capacite = float(trajet.capacite_restante_kg)
    poids = float(demande.poids_estime_kg)
    if capacite < poids:
        return 0
    if capacite == 0:
        return 0
    ratio = poids / capacite
    if ratio <= 0.5:
        return 100
    return max(10, round((1 - ratio) * 100, 2))


def score_trajet_pour_demande(demande: Demande, trajet: Trajet):
    """Calcule le score 0-100 d'un trajet pour une demande (None si inéligible)."""
    proximite = _score_proximite(demande, trajet)
    capacite = _score_capacite(demande, trajet)
    if proximite == 0 or capacite == 0:
        return None

    fiabilite = float(trajet.transporteur.score_fiabilite or 0)
    date = _score_date(demande, trajet)

    return round(
        PONDERATION["fiabilite"] * fiabilite
        + PONDERATION["proximite"] * proximite
        + PONDERATION["date"] * date
        + PONDERATION["capacite"] * capacite,
        2,
    )


def _base_trajets_actifs():
    """Trajets actifs, non expirés, de transporteurs réels (non-admin)."""
    maintenant = timezone.now()
    return (
        Trajet.objects.filter(
            statut=Trajet.StatutTrajet.ACTIF,
            date_depart__gte=maintenant,
            transporteur__est_transporteur=True,
        )
        .exclude(transporteur__type_compte__in=["admin"])
        .select_related("transporteur")
    )


def demande_a_une_course_active(demande: Demande) -> bool:
    """Une demande n'a qu'une course active à la fois ; une course annulée la
    rend de nouveau disponible au matching."""
    return demande.courses.exclude(statut="annulee").exists()


def _base_demandes_publiees():
    """Demandes publiées (validées par l'IA), sans course active : éligibles au matching."""
    return (
        Demande.objects.filter(statut=Demande.StatutDemande.PUBLIEE)
        .exclude(courses__statut__in=[
            "reservee", "proposition_montant", "en_attente_paiement", "payee",
            "depart", "en_route", "arrivee", "livree", "en_litige",
        ])
        .distinct()
    )


def matching_pour_client(demande: Demande):
    """Retourne la liste (trajet, score) classée pour une demande publiée.

    BF-10 : liste de transporteurs/trajets proposés au client, du plus optimal
    au moins optimal. On exclut les trajets du client lui-même (il ne
    transporte pas son propre colis via le matching).
    """
    resultats = []
    for trajet in _base_trajets_actifs():
        if trajet.transporteur_id == demande.client_id:
            continue
        score = score_trajet_pour_demande(demande, trajet)
        if score is not None:
            resultats.append({"trajet": trajet, "score": score})
    resultats.sort(key=lambda x: x["score"], reverse=True)
    return resultats


def matching_pour_transporteur(trajet: Trajet):
    """Retourne la liste (demande, score) classée pour un trajet actif.

    BF-27 : le transporteur consulte les demandes issues du matching
    correspondant à son trajet, et choisit celle(s) qu'il accepte.
    """
    resultats = []
    for demande in _base_demandes_publiees():
        # On exclut ses propres demandes (double rôle RM-04).
        if demande.client_id == trajet.transporteur_id:
            continue
        score = score_trajet_pour_demande(demande, trajet)
        if score is not None:
            resultats.append({"demande": demande, "score": score})
    resultats.sort(key=lambda x: x["score"], reverse=True)
    return resultats
