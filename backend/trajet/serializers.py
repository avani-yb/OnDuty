from rest_framework import serializers

from .models import Trajet
from .services import type_vehicule


class _DemandeCompactSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    origine = serializers.CharField()
    destination = serializers.CharField()
    description = serializers.CharField()
    poids_estime_kg = serializers.DecimalField(max_digits=10, decimal_places=2)
    montant_propose = serializers.DecimalField(max_digits=12, decimal_places=2)
    telephone_destinataire = serializers.CharField()


class _ClientCompactSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nom = serializers.CharField()
    prenom = serializers.CharField()
    telephone = serializers.CharField()


class CourseSurTrajetSerializer(serializers.Serializer):
    """Vue compacte d'une Course, pour l'affichage dans le détail d'un Trajet
    (le transporteur y voit les réservations reçues et peut y réagir)."""

    id = serializers.IntegerField()
    statut = serializers.CharField()
    initiee_par = serializers.CharField()
    montant_convenu = serializers.DecimalField(max_digits=12, decimal_places=2)
    demande = _DemandeCompactSerializer()
    client = _ClientCompactSerializer()


class TrajetSerializer(serializers.ModelSerializer):
    # Réservations reçues sur ce trajet (relation inverse `related_name="courses"`
    # sur Course.trajet) : nécessaire pour que le transporteur voie et traite
    # les demandes de réservation (accepter / proposer un autre montant).
    courses = CourseSurTrajetSerializer(many=True, read_only=True)
    etat = serializers.CharField(read_only=True)
    est_modifiable = serializers.BooleanField(read_only=True)
    kg_reserves = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    capacite_restante_kg = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)
    a_des_courses = serializers.SerializerMethodField()
    type_vehicule = serializers.SerializerMethodField()

    class Meta:
        model = Trajet
        fields = [
            "id",
            "transporteur",
            "origine",
            "destination",
            "date_depart",
            "capacite_disponible_kg",
            "statut",
            "etat",
            "est_modifiable",
            "kg_reserves",
            "capacite_restante_kg",
            "a_des_courses",
            "type_vehicule",
            "date_creation",
            "courses",
        ]
        read_only_fields = ["id", "transporteur", "statut", "date_creation", "courses"]

    def get_a_des_courses(self, obj):
        return obj.courses_actives().exists()

    def get_type_vehicule(self, obj):
        return type_vehicule(obj.transporteur)

    def validate_capacite_disponible_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "La capacité disponible doit être strictement positive."
            )
        return value

    def validate_date_depart(self, value):
        from django.utils import timezone

        if value < timezone.now():
            raise serializers.ValidationError(
                "La date de départ doit être dans le futur."
            )
        return value

    def validate(self, attrs):
        trajet = self.instance
        if trajet is None:
            return attrs

        # Modification (décision du 04/10/2026) : trajets « actifs » seulement ;
        # sans course tout est modifiable, avec des courses seule la capacité,
        # et jamais en dessous des kg déjà réservés.
        if not trajet.est_modifiable:
            raise serializers.ValidationError(
                "Seul un trajet actif (dont la date n'est pas encore arrivée) peut être modifié."
            )
        if trajet.courses_actives().exists():
            bloques = [
                champ for champ in ("origine", "destination", "date_depart")
                if champ in attrs and attrs[champ] != getattr(trajet, champ)
            ]
            if bloques:
                raise serializers.ValidationError(
                    "Ce trajet a déjà des courses : seule la capacité peut être modifiée. "
                    "Pour changer la date ou l'itinéraire, supprimez le trajet."
                )
        capacite = attrs.get("capacite_disponible_kg")
        if capacite is not None and capacite < trajet.kg_reserves:
            raise serializers.ValidationError({
                "capacite_disponible_kg": (
                    f"La capacité ne peut pas être inférieure aux {trajet.kg_reserves} kg déjà réservés."
                )
            })
        return attrs
