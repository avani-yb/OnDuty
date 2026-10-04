from rest_framework import serializers

from .models import Incident, Litige


class UtilisateurCompactSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nom = serializers.CharField()
    prenom = serializers.CharField()
    telephone = serializers.CharField()


class IncidentSerializer(serializers.ModelSerializer):
    transporteur = UtilisateurCompactSerializer(read_only=True)

    class Meta:
        model = Incident
        fields = [
            "id",
            "course",
            "transporteur",
            "description",
            "date_signalement",
        ]
        read_only_fields = fields


class IncidentCreerSerializer(serializers.ModelSerializer):
    """Sérialiseur pour créer un incident (transporteur uniquement)."""

    class Meta:
        model = Incident
        fields = ["id", "description"]
        read_only_fields = ["id"]


class LitigeSerializer(serializers.ModelSerializer):
    declarant = UtilisateurCompactSerializer(read_only=True)

    class Meta:
        model = Litige
        fields = [
            "id",
            "course",
            "declarant",
            "motif",
            "statut",
            "decision_admin",
            "date_declaration",
            "date_resolution",
        ]
        read_only_fields = fields


class LitigeCreerSerializer(serializers.ModelSerializer):
    """Sérialiseur pour créer un litige (client ou transporteur)."""

    class Meta:
        model = Litige
        fields = ["id", "motif"]
        read_only_fields = ["id"]


class LitigeTraiterSerializer(serializers.Serializer):
    """Sérialiseur pour le traitement admin d'un litige."""

    action = serializers.ChoiceField(choices=["resoudre", "prendre_en_charge"])
    decision = serializers.CharField(required=False, allow_blank=True)