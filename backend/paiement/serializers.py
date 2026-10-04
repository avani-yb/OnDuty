from rest_framework import serializers

from .models import Paiement, Versement

# Libellés affichés selon le rôle (décision du 04/10/2026).
LIBELLES_CLIENT = {
    Paiement.StatutPaiement.EN_ATTENTE: "En cours",
    Paiement.StatutPaiement.ECHOUE: "Échoué",
    Paiement.StatutPaiement.BLOQUE_ESCROW: "Effectué",
    Paiement.StatutPaiement.LIBERE: "Effectué",
    Paiement.StatutPaiement.REMBOURSE: "Remboursé",
}
LIBELLES_TRANSPORTEUR = {
    Paiement.StatutPaiement.BLOQUE_ESCROW: "En attente de livraison",
    Paiement.StatutPaiement.LIBERE: "Reçu",
    Paiement.StatutPaiement.REMBOURSE: "Course annulée",
}


class VersementSerializer(serializers.ModelSerializer):
    class Meta:
        model = Versement
        fields = ["id", "type_versement", "montant", "numero", "statut", "date_creation", "date_effectue"]
        read_only_fields = fields


class PaiementSerializer(serializers.ModelSerializer):
    """Lecture d'un paiement, adaptée au rôle de l'utilisateur connecté.

    `role` : client ou transporteur ; `statut_affiche` : libellé à montrer.
    Le transporteur voit le prix de la course (ce qu'il reçoit), le client
    le détail de ce qu'il a payé.
    """

    course = serializers.SerializerMethodField()
    role = serializers.SerializerMethodField()
    statut_affiche = serializers.SerializerMethodField()
    versements = VersementSerializer(many=True, read_only=True)

    class Meta:
        model = Paiement
        fields = [
            "id",
            "course",
            "role",
            "statut",
            "statut_affiche",
            "montant_course",
            "commission",
            "frais",
            "montant",
            "methode",
            "numero_payeur",
            "code_ussd",
            "message_erreur",
            "versements",
            "date_paiement",
            "date_liberation",
            "date_creation",
        ]
        read_only_fields = fields

    def _role(self, obj):
        utilisateur = getattr(self.context.get("request"), "user", None)
        if utilisateur is not None and utilisateur.pk == obj.course.transporteur_id:
            return "transporteur"
        return "client"

    def get_role(self, obj):
        return self._role(obj)

    def get_statut_affiche(self, obj):
        if self._role(obj) == "transporteur":
            if obj.statut == Paiement.StatutPaiement.LIBERE:
                verse = obj.versements.filter(
                    type_versement=Versement.TypeVersement.TRANSPORTEUR,
                    statut=Versement.StatutVersement.EFFECTUE,
                ).exists()
                return "Reçu" if verse else "Versement en cours"
            return LIBELLES_TRANSPORTEUR.get(obj.statut, obj.get_statut_display())
        return LIBELLES_CLIENT.get(obj.statut, obj.get_statut_display())

    def get_course(self, obj):
        course = obj.course
        return {
            "id": course.id,
            "statut": course.statut,
            "origine": course.demande.origine,
            "destination": course.demande.destination,
            "client": {"id": course.client.id, "nom": course.client.nom, "prenom": course.client.prenom},
            "transporteur": {
                "id": course.transporteur.id,
                "nom": course.transporteur.nom,
                "prenom": course.transporteur.prenom,
            },
        }

    def to_representation(self, obj):
        donnees = super().to_representation(obj)
        if donnees["role"] == "transporteur":
            # Le transporteur n'a pas à voir la commission ni le numéro du client.
            for champ in ("commission", "frais", "montant", "numero_payeur", "code_ussd"):
                donnees.pop(champ, None)
        return donnees


class PaiementInitierSerializer(serializers.Serializer):
    """Le client lance le paiement depuis le numéro Mobile Money de son choix."""

    numero = serializers.CharField(max_length=20)
