from rest_framework import serializers


class TransporteurCompactSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nom = serializers.CharField()
    prenom = serializers.CharField()
    telephone = serializers.CharField()
    score_fiabilite = serializers.DecimalField(max_digits=4, decimal_places=2)


class TrajetMatchingSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    origine = serializers.CharField()
    destination = serializers.CharField()
    date_depart = serializers.DateTimeField()
    capacite_disponible_kg = serializers.DecimalField(
        max_digits=10, decimal_places=2
    )
    transporteur = TransporteurCompactSerializer()
    type_vehicule = serializers.CharField(allow_null=True)


class ResultatClientSerializer(serializers.Serializer):
    """Une proposition de matching vue par le client (BF-10)."""

    score = serializers.FloatField()
    trajet = TrajetMatchingSerializer()


class ResultatTransporteurSerializer(serializers.Serializer):
    """Une demande issue du matching vue par le transporteur (BF-27)."""

    score = serializers.FloatField()
    demande = serializers.SerializerMethodField()

    def get_demande(self, obj):
        demande = obj["demande"]
        return {
            "id": demande.id,
            "origine": demande.origine,
            "destination": demande.destination,
            "date_souhaitee": demande.date_souhaitee,
            "description": demande.description,
            "poids_estime_kg": demande.poids_estime_kg,
            "montant_propose": demande.montant_propose,
            # Détails extraits par le contrôle IA (doc 12, section 5) : le
            # transporteur sait ce qu'il transportera avant de s'engager.
            "details_visuels": _details_visuels(demande),
        }


def _details_visuels(demande):
    controle = demande.controles.filter(verdict="valide").order_by("-numero_tentative").first()
    if controle and isinstance(controle.resultat_coherence, dict):
        return controle.resultat_coherence.get("détails_visuels")
    return None
