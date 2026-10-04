from rest_framework import serializers

from .models import InformationsVehicule


class InformationsVehiculeSerializer(serializers.ModelSerializer):
    """Sérialiseur des informations véhicule du transporteur.

    Le champ `utilisateur` est en lecture seule : il est imposé par le serveur
    (l'utilisateur connecté ne peut renseigner que SON véhicule).
    """

    class Meta:
        model = InformationsVehicule
        fields = [
            "id",
            "utilisateur",
            "type_vehicule",
            "marque",
            "modele",
            "immatriculation",
            "capacite_max_kg",
        ]
        read_only_fields = ["id", "utilisateur"]

    def validate(self, attrs):
        # Un utilisateur ne peut avoir qu'UN seul véhicule (relation OneToOne).
        # On vérifie dans l'objet serializer plutôt que d'attendre une erreur
        # de base de données (IntegrityError) pour renvoyer un message clair.
        utilisateur = self.context["request"].user
        existe_deja = (
            InformationsVehicule.objects
            .filter(utilisateur=utilisateur)
            .exclude(pk=self.instance.pk if self.instance else None)
            .exists()
        )
        if existe_deja:
            raise serializers.ValidationError(
                "Un véhicule existe déjà pour ce compte. "
                "Modifiez le véhicule existant plutôt que d'en créer un second."
            )
        return attrs
