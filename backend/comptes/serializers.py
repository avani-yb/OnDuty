from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Utilisateur


class UtilisateurSerializer(serializers.ModelSerializer):
    """Sérialiseur en lecture des données publiques du profil."""

    class Meta:
        model = Utilisateur
        fields = [
            "id",
            "nom",
            "prenom",
            "telephone",
            "email",
            "numero_mobile_money",
            "photo_profil",
            "est_transporteur",
            "type_compte",
            "score_fiabilite",
            "statut_compte",
            "date_creation",
        ]
        read_only_fields = [
            "id",
            "est_transporteur",
            "type_compte",
            "score_fiabilite",
            "statut_compte",
            "date_creation",
        ]

    def validate_numero_mobile_money(self, value):
        """Vide = téléphone du compte ; sinon un numéro mobile camerounais."""
        if not value:
            return ""
        from paiement.services.campay import NumeroInvalide, normaliser_numero

        try:
            return normaliser_numero(value)
        except NumeroInvalide as exc:
            raise serializers.ValidationError(str(exc))


class InscriptionSerializer(serializers.ModelSerializer):
    """Sérialiseur utilisé lors de la création d'un nouveau compte.

    Le mot de passe est reçu en clair mais n'est jamais retourné :
    il est hashé et stocké via `create_user`.
    """

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={"input_type": "password"},
    )

    class Meta:
        model = Utilisateur
        fields = [
            "nom",
            "prenom",
            "telephone",
            "email",
            "password",
        ]

    def validate_telephone(self, value):
        """Normalise le numéro de téléphone (uniquement chiffres)."""
        normalise = "".join(ch for ch in value if ch.isdigit())
        if not normalise:
            raise serializers.ValidationError("Numéro de téléphone invalide.")
        return normalise

    def create(self, validated_data):
        # `create_user` s'occupe de hacher le mot de passe.
        return Utilisateur.objects.create_user(**validated_data)


class ModificationMotDePasseSerializer(serializers.Serializer):
    """Sérialiseur pour changer son propre mot de passe (BF-18)."""

    ancien_mot_de_passe = serializers.CharField(
        write_only=True, style={"input_type": "password"}
    )
    nouveau_mot_de_passe = serializers.CharField(
        write_only=True, validators=[validate_password],
        style={"input_type": "password"},
    )

    def validate_ancien_mot_de_passe(self, value):
        utilisateur = self.context["request"].user
        if not utilisateur.check_password(value):
            raise serializers.ValidationError("L'ancien mot de passe est incorrect.")
        return value

    def save(self, **kwargs):
        utilisateur = self.context["request"].user
        utilisateur.set_password(self.validated_data["nouveau_mot_de_passe"])
        utilisateur.save(update_fields=["password"])
        return utilisateur
