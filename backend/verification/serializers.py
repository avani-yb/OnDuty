from rest_framework import serializers

from .models import Verification

TAILLE_MAX_IMAGE = 8 * 1024 * 1024  # 8 Mo par photo


class VerificationSerializer(serializers.ModelSerializer):
    """Sérialiseur d'une demande de vérification (KYC).

    Le client SOUMET une vérification (statut `en_attente`) avec ses photos :
    pour une CNI, le recto et un selfie sont obligatoires, le verso conseillé.
    Le `numero_tentative` est calculé automatiquement pour préserver
    l'historique. Les photos ne sont jamais renvoyées par URL : elles sont
    consultables via `GET /verifications/{id}/document/{champ}/`.
    """

    cni_recto = serializers.ImageField(write_only=True, required=False)
    cni_verso = serializers.ImageField(write_only=True, required=False)
    selfie = serializers.ImageField(write_only=True, required=False)
    documents = serializers.SerializerMethodField()

    class Meta:
        model = Verification
        fields = [
            "id",
            "utilisateur",
            "type_verification",
            "statut",
            "motif",
            "fournisseur",
            "date_soumission",
            "date_traitement",
            "resultat_brut",
            "numero_tentative",
            "cni_recto",
            "cni_verso",
            "selfie",
            "documents",
        ]
        read_only_fields = [
            "id",
            "utilisateur",
            "statut",
            "motif",
            "fournisseur",
            "date_soumission",
            "date_traitement",
            "resultat_brut",
            "numero_tentative",
        ]

    def get_documents(self, obj):
        """Liste des photos présentes (sans URL publique)."""
        return [champ for champ in ("cni_recto", "cni_verso", "selfie") if getattr(obj, champ)]

    def validate(self, attrs):
        utilisateur = self.context["request"].user
        type_verification = attrs["type_verification"]

        en_cours = Verification.objects.filter(
            utilisateur=utilisateur,
            type_verification=type_verification,
            statut__in=[
                Verification.StatutVerification.EN_ATTENTE,
                Verification.StatutVerification.A_REVOIR,
                Verification.StatutVerification.VALIDEE,
            ],
        ).first()
        if en_cours:
            if en_cours.statut == Verification.StatutVerification.VALIDEE:
                message = "Cette vérification a déjà été validée."
            else:
                message = "Une vérification est déjà en cours de traitement."
            raise serializers.ValidationError({"type_verification": message})

        if type_verification == Verification.TypeVerification.CNI:
            manquants = {
                champ: "Cette photo est obligatoire."
                for champ in ("cni_recto", "selfie")
                if not attrs.get(champ)
            }
            if manquants:
                raise serializers.ValidationError(manquants)

        for champ in ("cni_recto", "cni_verso", "selfie"):
            image = attrs.get(champ)
            if image and image.size > TAILLE_MAX_IMAGE:
                raise serializers.ValidationError({champ: "La photo dépasse 8 Mo."})
        return attrs

    def create(self, validated_data):
        utilisateur = self.context["request"].user
        type_verification = validated_data["type_verification"]

        # Calcul du numéro de tentative : on compte les tentatives existantes
        # du même type pour le même utilisateur, puis on ajoute 1.
        nb_existantes = Verification.objects.filter(
            utilisateur=utilisateur,
            type_verification=type_verification,
        ).count()
        return Verification.objects.create(
            utilisateur=utilisateur,
            numero_tentative=nb_existantes + 1,
            **validated_data,
        )


class TraitementVerificationSerializer(serializers.ModelSerializer):
    """Sérialiseur réservé à l'administrateur pour traiter une vérification.

    Permet de fixer le statut (validée/rejetée/à revoir), le motif affiché à
    l'utilisateur et le résultat brut, ainsi que la date de traitement.
    """

    class Meta:
        model = Verification
        fields = [
            "statut",
            "motif",
            "resultat_brut",
        ]

    def update(self, instance, validated_data):
        # On horodate la date de traitement lors de la clôture de la demande.
        instance.date_traitement = validated_data.pop("date_traitement", None)
        if validated_data.get("statut") in (
            Verification.StatutVerification.VALIDEE,
            Verification.StatutVerification.REJETEE,
        ):
            from django.utils import timezone

            instance.date_traitement = timezone.now()
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        return instance
