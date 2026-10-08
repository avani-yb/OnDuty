from rest_framework import serializers

from .models import Course


class UtilisateurCompactSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    nom = serializers.CharField()
    prenom = serializers.CharField()
    telephone = serializers.CharField()
    score_fiabilite = serializers.DecimalField(max_digits=4, decimal_places=2, required=False, allow_null=True)


class DemandeCompactSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    origine = serializers.CharField()
    destination = serializers.CharField()
    date_souhaitee = serializers.DateTimeField()
    poids_estime_kg = serializers.DecimalField(max_digits=10, decimal_places=2)
    montant_propose = serializers.DecimalField(max_digits=12, decimal_places=2)
    description = serializers.CharField()
    telephone_destinataire = serializers.CharField()


class TrajetCompactSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    origine = serializers.CharField()
    destination = serializers.CharField()
    date_depart = serializers.DateTimeField()
    capacite_disponible_kg = serializers.DecimalField(max_digits=10, decimal_places=2)
    transporteur = UtilisateurCompactSerializer()


class CourseSerializer(serializers.ModelSerializer):
    """Sérialiseur complet pour la lecture d'une course.

    `role` indique la place de l'utilisateur connecté dans la course
    (client / transporteur / destinataire), pour adapter l'affichage.
    """

    demande = DemandeCompactSerializer(read_only=True)
    trajet = TrajetCompactSerializer(read_only=True)
    client = UtilisateurCompactSerializer(read_only=True)
    transporteur = UtilisateurCompactSerializer(read_only=True)
    destinataire = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    peut_confirmer_reception = serializers.SerializerMethodField()
    details_visuels = serializers.SerializerMethodField()
    type_vehicule = serializers.SerializerMethodField()
    paiement = serializers.SerializerMethodField()
    suivi_disponible = serializers.SerializerMethodField()

    class Meta:
        model = Course
        fields = [
            "id",
            "demande",
            "trajet",
            "client",
            "transporteur",
            "destinataire",
            "role",
            "statut",
            "initiee_par",
            "motif_annulation",
            "montant_convenu",
            "peut_confirmer_reception",
            "suivi_disponible",
            "details_visuels",
            "type_vehicule",
            "paiement",
            "date_creation",
            "date_depart_reel",
            "date_livraison",
        ]
        read_only_fields = fields

    def _utilisateur(self):
        requete = self.context.get("request")
        return getattr(requete, "user", None)

    def get_destinataire(self, obj):
        destinataire = obj.demande.destinataire
        if destinataire is None:
            return None
        return {"id": destinataire.id, "nom": destinataire.nom, "prenom": destinataire.prenom}

    def get_role(self, obj):
        utilisateur = self._utilisateur()
        if utilisateur is None:
            return None
        if utilisateur.pk == obj.client_id:
            return "client"
        if utilisateur.pk == obj.transporteur_id:
            return "transporteur"
        if utilisateur.pk == obj.demande.destinataire_id:
            return "destinataire"
        return "admin" if getattr(utilisateur, "est_admin", False) else None

    def get_suivi_disponible(self, obj):
        from .models import STATUTS_SUIVI

        return obj.statut in STATUTS_SUIVI

    def get_peut_confirmer_reception(self, obj):
        utilisateur = self._utilisateur()
        return obj.statut == Course.StatutCourse.ARRIVEE and obj.peut_confirmer_reception(utilisateur)

    def get_details_visuels(self, obj):
        controle = obj.demande.controles.filter(verdict="valide").order_by("-numero_tentative").first()
        if controle and isinstance(controle.resultat_coherence, dict):
            return controle.resultat_coherence.get("détails_visuels")
        return None

    def get_type_vehicule(self, obj):
        from trajet.services import type_vehicule

        return type_vehicule(obj.transporteur)

    def get_paiement(self, obj):
        paiement = getattr(obj, "paiement", None)
        if paiement is None:
            return None
        return {"id": paiement.id, "statut": paiement.statut, "montant": paiement.montant}


def _verifier_trajet_pour_demande(demande, trajet):
    """Règles communes aux deux façons de créer une course."""
    from matching.services.matching import demande_a_une_course_active, score_trajet_pour_demande
    from trajet.models import Trajet

    if trajet.statut != Trajet.StatutTrajet.ACTIF or trajet.etat == Trajet.ETAT_PASSE:
        raise serializers.ValidationError("Ce trajet n'est plus actif.")
    if demande.statut != demande.StatutDemande.PUBLIEE:
        raise serializers.ValidationError("La demande n'est pas publiée (contrôle IA non validé).")
    if demande.client_id == trajet.transporteur_id:
        raise serializers.ValidationError("Vous ne pouvez pas transporter votre propre demande.")
    if demande_a_une_course_active(demande):
        raise serializers.ValidationError("Cette demande a déjà une course en cours.")
    if trajet.capacite_restante_kg < demande.poids_estime_kg:
        raise serializers.ValidationError("Capacité insuffisante sur ce trajet.")
    if score_trajet_pour_demande(demande, trajet) is None:
        raise serializers.ValidationError("Le trajet ne correspond pas à l'itinéraire de la demande.")


class CourseCreerSerializer(serializers.ModelSerializer):
    """Création d'une course par le client : il choisit un trajet du matching."""

    trajet_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = Course
        fields = ["id", "trajet_id"]
        read_only_fields = ["id"]

    def validate_trajet_id(self, value):
        from trajet.models import Trajet

        try:
            trajet = Trajet.objects.select_related("transporteur").get(pk=value)
        except Trajet.DoesNotExist:
            raise serializers.ValidationError("Trajet introuvable.")
        _verifier_trajet_pour_demande(self.context["demande"], trajet)
        self.context["trajet"] = trajet
        return value

    def create(self, validated_data):
        demande = self.context["demande"]
        trajet = self.context["trajet"]
        return Course.objects.create(
            demande=demande,
            trajet=trajet,
            client=demande.client,
            transporteur=trajet.transporteur,
            statut=Course.StatutCourse.RESERVEE,
            initiee_par=Course.InitiePar.CLIENT,
            montant_convenu=demande.montant_propose,
        )


class CourseProposerSerializer(serializers.Serializer):
    """Le transporteur choisit une demande compatible avec l'un de ses trajets.

    `montant` est facultatif : sans montant, le prix proposé par le client
    est repris. Le client doit ensuite accepter (puis payer) ou refuser.
    """

    demande_id = serializers.IntegerField()
    trajet_id = serializers.IntegerField()
    montant = serializers.DecimalField(max_digits=12, decimal_places=2, required=False)

    def validate_montant(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être strictement positif.")
        return value

    def validate(self, attrs):
        from demande.models import Demande
        from trajet.models import Trajet

        utilisateur = self.context["request"].user
        try:
            trajet = Trajet.objects.select_related("transporteur").get(
                pk=attrs["trajet_id"], transporteur=utilisateur
            )
        except Trajet.DoesNotExist:
            raise serializers.ValidationError({"trajet_id": "Trajet introuvable."})
        try:
            demande = Demande.objects.select_related("client").get(pk=attrs["demande_id"])
        except Demande.DoesNotExist:
            raise serializers.ValidationError({"demande_id": "Demande introuvable."})
        if not trajet.est_modifiable:
            raise serializers.ValidationError("Seul un trajet actif peut recevoir de nouvelles demandes.")
        _verifier_trajet_pour_demande(demande, trajet)
        attrs["trajet"] = trajet
        attrs["demande"] = demande
        return attrs

    def create(self, validated_data):
        demande = validated_data["demande"]
        trajet = validated_data["trajet"]
        return Course.objects.create(
            demande=demande,
            trajet=trajet,
            client=demande.client,
            transporteur=trajet.transporteur,
            statut=Course.StatutCourse.PROPOSITION_MONTANT,
            initiee_par=Course.InitiePar.TRANSPORTEUR,
            montant_convenu=validated_data.get("montant") or demande.montant_propose,
        )


class ProposerMontantSerializer(serializers.Serializer):
    """Sérialiseur pour la contre-proposition de montant par le transporteur."""

    montant = serializers.DecimalField(max_digits=12, decimal_places=2)

    def validate_montant(self, value):
        if value <= 0:
            raise serializers.ValidationError("Le montant doit être strictement positif.")
        return value
