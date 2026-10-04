"""Service de calcul du score de fiabilité du transporteur.

Le score_fiabilite (sur Utilisateur) est un score composite recalculé après
chaque course, intégrant 4 facteurs (doc 10-diagramme-classes.md §3) :

1. **Moyenne des notes** (Evaluations reçues) — poids principal
2. **Taux de ponctualité** : courses où statuts mis à jour dans les délais
3. **Incidents signalés** — facteur pénalisant
4. **Litiges où jugé responsable** — facteur pénalisant
5. **Courses annulées par suppression du trajet** — facteur pénalisant
   (décision du 04/10/2026 : −5 points par course annulée)

Formule : score = (moyenne_notes * 0.5) + (ponctualité * 0.3) - (incidents * 2)
                  - (litiges_responsable * 3) - (courses_annulees_trajet * 5)
Résultat borné entre 0 et 100.
"""

from django.db.models import Avg, Count
from django.utils import timezone

from course.models import Course
from litige.models import Incident, Litige
from evaluation.models import Evaluation

PENALITE_COURSE_ANNULEE_TRAJET = 5.0


def _nb_courses_annulees_trajet(transporteur):
    """Courses annulées parce que le transporteur a supprimé son trajet."""
    return Course.objects.filter(
        transporteur=transporteur,
        statut=Course.StatutCourse.ANNULEE,
        motif_annulation=Course.MotifAnnulation.SUPPRESSION_TRAJET,
    ).count()


def calculer_score_fiabilite(transporteur):
    """Calcule et met à jour le score_fiabilite d'un transporteur.

    Appelé automatiquement à chaque nouvelle Evaluation (via model.save()).
    Peut aussi être appelé manuellement (ex. après résolution litige).
    """
    # 1. Moyenne des notes (sur 5, convertie sur 100)
    avg_note = Evaluation.objects.filter(transporteur=transporteur).aggregate(
        avg=Avg("note")
    )["avg"]
    if avg_note is None:
        score_notes = 50  # Neutre si pas d'évaluation
    else:
        score_notes = (avg_note / 5) * 100  # 1-5 → 20-100

    # 2. Taux de ponctualité
    # Courses terminées (livree) du transporteur
    courses_terminees = Course.objects.filter(
        transporteur=transporteur,
        statut=Course.StatutCourse.LIVREE,
    )
    total_terminees = courses_terminees.count()

    if total_terminees > 0:
        # Ponctuel = date_depart_reel et date_livraison non nulles (statuts mis à jour)
        # On considère ponctuel si la course a bien suivi le cycle normal
        ponctuelles = courses_terminees.exclude(
            date_depart_reel__isnull=True
        ).exclude(
            date_livraison__isnull=True
        ).count()
        taux_ponctualite = (ponctuelles / total_terminees) * 100
    else:
        taux_ponctualite = 100  # Neutre si pas de course terminée

    # 3. Incidents signalés (facteur pénalisant)
    nb_incidents = Incident.objects.filter(
        transporteur=transporteur
    ).count()

    # 4. Litiges où jugé responsable (statut resolu avec décision défavorable)
    # Pour simplifier : on compte les litiges résolus où le transporteur n'est pas le déclarant
    # et qui ont abouti à une décision (remboursement, etc.)
    nb_litiges_responsable = Litige.objects.filter(
        course__transporteur=transporteur,
        statut=Litige.StatutLitige.RESOLU,
    ).exclude(declarant=transporteur).count()

    # 5. Courses annulées suite à la suppression d'un trajet
    nb_annulees_trajet = _nb_courses_annulees_trajet(transporteur)

    # Formule composite (pondération selon priorité métier)
    # Notes: 50%, Ponctualité: 30%, Incidents: -2 pts chacun, Litiges: -3 pts chacun
    score = (
        score_notes * 0.50
        + taux_ponctualite * 0.30
        - nb_incidents * 2.0
        - nb_litiges_responsable * 3.0
        - nb_annulees_trajet * PENALITE_COURSE_ANNULEE_TRAJET
    )

    # Borner entre 0 et 100
    score = max(0, min(100, round(score, 2)))

    # Mise à jour
    transporteur.score_fiabilite = score
    transporteur.save(update_fields=["score_fiabilite"])

    return score


def get_details_fiabilite(transporteur):
    """Retourne le détail des composantes du score pour affichage/debug."""
    avg_note = Evaluation.objects.filter(transporteur=transporteur).aggregate(
        avg=Avg("note"), count=Count("id")
    )
    courses_terminees = Course.objects.filter(
        transporteur=transporteur, statut=Course.StatutCourse.LIVREE
    )
    total_terminees = courses_terminees.count()
    ponctuelles = 0
    if total_terminees > 0:
        ponctuelles = courses_terminees.exclude(
            date_depart_reel__isnull=True
        ).exclude(date_livraison__isnull=True).count()

    nb_incidents = Incident.objects.filter(transporteur=transporteur).count()
    nb_litiges_responsable = Litige.objects.filter(
        course__transporteur=transporteur, statut=Litige.StatutLitige.RESOLU
    ).exclude(declarant=transporteur).count()

    score_notes = (avg_note["avg"] / 5 * 100) if avg_note["avg"] else 50
    taux_ponctualite = (ponctuelles / total_terminees * 100) if total_terminees else 100

    return {
        "score_global": transporteur.score_fiabilite,
        "moyenne_notes": round(avg_note["avg"] or 0, 2),
        "nb_evaluations": avg_note["count"] or 0,
        "score_notes_pondere": round(score_notes * 0.50, 2),
        "taux_ponctualite": round(taux_ponctualite, 2),
        "score_ponctualite_pondere": round(taux_ponctualite * 0.30, 2),
        "nb_incidents": nb_incidents,
        "penalite_incidents": nb_incidents * 2.0,
        "nb_litiges_responsable": nb_litiges_responsable,
        "penalite_litiges": nb_litiges_responsable * 3.0,
        "nb_courses_annulees_trajet": _nb_courses_annulees_trajet(transporteur),
        "penalite_courses_annulees_trajet": (
            _nb_courses_annulees_trajet(transporteur) * PENALITE_COURSE_ANNULEE_TRAJET
        ),
    }