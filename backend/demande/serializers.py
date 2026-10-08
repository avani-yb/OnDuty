from django.conf import settings
from rest_framework import serializers

from onduty_backend import localites

from .models import ContestationRejet, ControleIA, Demande


class DemandeSerializer(serializers.ModelSerializer):
    """Demande d'expédition.

    Les champs d'audit (client, statut, date_creation) sont en lecture seule.
    La création place la demande en `en_cours_controle` (le contrôle IA est
    déclenché dans la vue).

    `telephone_destinataire` : si ce numéro correspond à un compte OnDuty, ce
    compte devient le destinataire (notifié, voit la course, peut confirmer
    la réception). Sinon le numéro sert d'information au transporteur.
    """

    destinataire = serializers.SerializerMethodField()
    course_active = serializers.SerializerMethodField()
    dernier_controle = serializers.SerializerMethodField()

    class Meta:
        model = Demande
        fields = [
            "id",
            "client",
            "origine",
            "destination",
            "date_souhaitee",
            "description",
            "poids_estime_kg",
            "montant_propose",
            "video",
            "video_url",
            "telephone_destinataire",
            "destinataire",
            "statut",
            "course_active",
            "dernier_controle",
            "date_creation",
        ]
        read_only_fields = ["id", "client", "statut", "date_creation", "video_url"]

    def get_destinataire(self, obj):
        if obj.destinataire is None:
            return None
        return {"id": obj.destinataire.id, "prenom": obj.destinataire.prenom, "nom": obj.destinataire.nom}

    def get_course_active(self, obj):
        course = obj.courses.exclude(statut="annulee").order_by("-date_creation").first()
        if course is None:
            return None
        return {"id": course.id, "statut": course.statut}

    def get_dernier_controle(self, obj):
        controle = obj.controles.order_by("-numero_tentative").first()
        if controle is None:
            return None
        contestation = controle.contestations.order_by("-date_soumission").first()
        return {
            "id": controle.id,
            "verdict": controle.verdict,
            "motif_rejet": controle.motif_rejet,
            "contestation": contestation.statut if contestation else None,
        }

    def validate_telephone_destinataire(self, value):
        chiffres = "".join(c for c in value if c.isdigit())
        if value and not 8 <= len(chiffres) <= 15:
            raise serializers.ValidationError("Numéro du destinataire invalide.")
        return chiffres

    def save(self, **kwargs):
        instance = super().save(**kwargs)
        if "telephone_destinataire" in self.validated_data:
            from comptes.models import chercher_par_telephone

            destinataire = chercher_par_telephone(instance.telephone_destinataire)
            if destinataire is not None and destinataire.pk == instance.client_id:
                destinataire = None  # le client s'envoie un colis à lui-même
            if destinataire != instance.destinataire:
                instance.destinataire = destinataire
                instance.save(update_fields=["destinataire"])
        return instance
        extra_kwargs = {"video": {"write_only": True, "required": False}}

    def validate(self, attrs):
        if self.instance is not None:
            # Mise à jour partielle (relance) : la vidéo existante est gardée
            # si aucune nouvelle n'est envoyée.
            return attrs
        if settings.IA_FOURNISSEUR == "reel" and not attrs.get("video"):
            # Le contrôle réel analyse le fichier vidéo lui-même.
            raise serializers.ValidationError(
                {"video": "Le fichier vidéo de l'article est requis."}
            )
        # La vidéo doit être fournie soit via un fichier envoyé depuis
        # l'app mobile (`video`), soit via une URL déjà hébergée
        # (`video_url`). Les deux ne peuvent pas être absentes.
        if not attrs.get("video") and not (self.initial_data.get("video_url") or "").strip():
            raise serializers.ValidationError(
                {"video": "Une vidéo (fichier ou URL) est requise."}
            )
        return attrs

    def create(self, validated_data):
        video_file = validated_data.pop("video", None)
        instance = Demande.objects.create(**validated_data)
        if video_file:
            # On affecte puis sauvegarde d'abord le fichier : c'est cet appel
            # à save() qui déclenche l'écriture réelle sur le storage et
            # applique `upload_to` pour générer le chemin final. `.url` ne
            # doit être lu qu'après, sinon il renvoie le nom de fichier brut.
            instance.video = video_file
            instance.save(update_fields=["video"])
            instance.video_url = instance.video.url
            instance.save(update_fields=["video_url"])
        return instance

    def update(self, instance, validated_data):
        video_file = validated_data.pop("video", None)
        instance = super().update(instance, validated_data)
        if video_file:
            instance.video = video_file
            instance.save(update_fields=["video"])
            instance.video_url = instance.video.url
            instance.save(update_fields=["video_url"])
        return instance

    def validate_origine(self, value):
        return localites.valider(value)

    def validate_destination(self, value):
        return localites.valider(value)

    def validate_poids_estime_kg(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "Le poids estimé doit être strictement positif."
            )
        return value

    def validate_montant_propose(self, value):
        if value <= 0:
            raise serializers.ValidationError(
                "La somme proposée doit être strictement positive."
            )
        return value

    def validate_date_souhaitee(self, value):
        from django.utils import timezone

        if value < timezone.now():
            raise serializers.ValidationError(
                "La date souhaitée doit être dans le futur."
            )
        return value


class ControleIASerializer(serializers.ModelSerializer):
    """Résultat d'un contrôle IA (lecture seule pour le client)."""

    demande = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = ControleIA
        fields = [
            "id",
            "demande",
            "numero_tentative",
            "resultat_detection_objets",
            "resultat_coherence",
            "verdict",
            "motif_rejet",
            "date_execution",
            "duree_traitement_secondes",
        ]
        read_only_fields = fields


class ContestationRejetSerializer(serializers.ModelSerializer):
    """Contestation d'un rejet par le client (BF-08)."""

    class Meta:
        model = ContestationRejet
        fields = [
            "id",
            "controle_ia",
            "client",
            "statut",
            "commentaire_admin",
            "date_soumission",
            "date_traitement",
        ]
        read_only_fields = [
            "id",
            "client",
            "statut",
            "commentaire_admin",
            "date_soumission",
            "date_traitement",
        ]


class TraiterContestationSerializer(serializers.ModelSerializer):
    """Traitement d'une contestation par l'administrateur (BF-08)."""

    class Meta:
        model = ContestationRejet
        fields = [
            "statut",
            "commentaire_admin",
        ]

    def update(self, instance, validated_data):
        from django.utils import timezone

        instance.statut = validated_data.get(
            "statut", instance.statut
        )
        instance.commentaire_admin = validated_data.get(
            "commentaire_admin", instance.commentaire_admin
        )
        instance.date_traitement = timezone.now()

        # Si l'admin infirme la décision de l'IA, la demande rejetée devient
        # éligible (publiée) — le rejet était injustifié (BF-08).
        if instance.statut == ContestationRejet.StatutContestation.INFIRMEE:
            demande = instance.controle_ia.demande
            if demande.statut == Demande.StatutDemande.REJETEE:
                demande.statut = Demande.StatutDemande.PUBLIEE
                demande.save(update_fields=["statut"])

        instance.save()

        if instance.statut != ContestationRejet.StatutContestation.EN_ATTENTE:
            from notification.models import Notification
            from notification.services.notifier import notifier

            infirmee = instance.statut == ContestationRejet.StatutContestation.INFIRMEE
            notifier(
                instance.client, Notification.TypeNotification.CONTROLE_IA,
                "Contestation acceptée" if infirmee else "Contestation refusée",
                (
                    "L'administrateur a validé votre demande : elle est maintenant visible par les transporteurs."
                    if infirmee
                    else "L'administrateur a confirmé le rejet de votre demande."
                )
                + (f" Commentaire : {instance.commentaire_admin}" if instance.commentaire_admin else ""),
                demande_id=instance.controle_ia.demande_id,
            )
        return instance
