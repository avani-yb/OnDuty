"""Supprime les positions GPS des courses terminées depuis plus d'un mois.

Politique de rétention (docs/14, section 5, appliquée au suivi GPS) : la
trace reste disponible un mois pour un éventuel litige, puis est effacée.
À lancer par une tâche planifiée (ex. une fois par jour) :

    python manage.py purger_positions
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from course.models import Course, PositionTransporteur

DUREE_CONSERVATION = timedelta(days=30)


class Command(BaseCommand):
    help = "Supprime les positions GPS des courses terminées depuis plus d'un mois."

    def handle(self, *args, **options):
        limite = timezone.now() - DUREE_CONSERVATION
        terminees = PositionTransporteur.objects.filter(
            course__statut__in=[Course.StatutCourse.LIVREE, Course.StatutCourse.ANNULEE],
            date__lt=limite,
        )
        # Courses livrées : on compte à partir de la livraison.
        livrees_recemment = Course.objects.filter(
            statut=Course.StatutCourse.LIVREE, date_livraison__gte=limite
        )
        nombre, _ = terminees.exclude(course__in=livrees_recemment).delete()
        self.stdout.write(f"{nombre} position(s) supprimée(s).")
