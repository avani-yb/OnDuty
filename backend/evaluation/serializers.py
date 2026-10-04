from rest_framework import serializers

from .models import Evaluation


class UtilisateurCompactSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nom = serializers.CharField()
    prenom = serializers.CharField()
    telephone = serializers.CharField()
    score_fiabilite = serializers.DecimalField(max_digits=5, decimal_places=2, required=False, allow_null=True)


class CourseCompactSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    origine = serializers.CharField(source="demande.origine")
    destination = serializers.CharField(source="demande.destination")
    date_creation = serializers.DateTimeField()


class EvaluationSerializer(serializers.ModelSerializer):
    """Sérialiseur complet pour lecture d'une évaluation."""

    client = UtilisateurCompactSerializer(read_only=True)
    transporteur = UtilisateurCompactSerializer(read_only=True)
    course = CourseCompactSerializer(read_only=True)

    class Meta:
        model = Evaluation
        fields = [
            "id",
            "course",
            "client",
            "transporteur",
            "note",
            "commentaire",
            "date_evaluation",
        ]
        read_only_fields = fields


class EvaluationCreerSerializer(serializers.ModelSerializer):
    """Sérialiseur pour créer une évaluation (client après course livrée)."""

    class Meta:
        model = Evaluation
        fields = ["id", "note", "commentaire"]
        read_only_fields = ["id"]

    def validate_note(self, value):
        if not 1 <= value <= 5:
            raise serializers.ValidationError("La note doit être entre 1 et 5.")
        return value