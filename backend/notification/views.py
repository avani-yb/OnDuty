from django.conf import settings
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import FCMToken, Notification
from .permissions import (
    AdminOuSystemeNotification,
    EstProprietaireFCMToken,
    EstProprietaireNotification,
    PeutCreerFCMToken,
)
from .serializers import (
    FCMTokenEnregistrerSerializer,
    FCMTokenSerializer,
    NotificationCreerSerializer,
    NotificationSerializer,
)
from .services.fcm import envoyer_notification_utilisateur, fcm_service
from comptes.models import Utilisateur


class FCMTokenViewSet(viewsets.ModelViewSet):
    """Gestion des tokens FCM (enregistrement depuis l'app mobile).

    - POST /fcm-tokens/ : enregistre un token FCM (appareil)
    - GET /fcm-tokens/ : liste ses tokens
    - DELETE /fcm-tokens/{id}/ : supprime/désactive un token
    """

    queryset = FCMToken.objects.all()
    serializer_class = FCMTokenSerializer
    permission_classes = [permissions.IsAuthenticated, EstProprietaireFCMToken]

    def get_queryset(self):
        return self.queryset.filter(utilisateur=self.request.user)

    def get_serializer_class(self):
        if self.action == "create":
            return FCMTokenEnregistrerSerializer
        return FCMTokenSerializer

    def get_permissions(self):
        if self.action == "create":
            return [permissions.IsAuthenticated(), PeutCreerFCMToken()]
        return super().get_permissions()

    def create(self, request, *args, **kwargs):
        """Enregistre ou met à jour un token FCM pour l'utilisateur connecté."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        token_value = serializer.validated_data["token"]
        device_id = serializer.validated_data.get("device_id", "")
        platform = serializer.validated_data.get("platform", "android")

        # Mettre à jour si existe, sinon créer
        fcm_token, created = FCMToken.objects.update_or_create(
            utilisateur=request.user,
            token=token_value,
            defaults={
                "device_id": device_id,
                "platform": platform,
                "actif": True,
            },
        )

        output_serializer = FCMTokenSerializer(fcm_token)
        return Response(output_serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["post"])
    def desactiver(self, request, pk=None):
        """Désactive un token (logout appareil)."""
        fcm_token = self.get_object()
        fcm_token.actif = False
        fcm_token.save(update_fields=["actif"])
        return Response({"detail": "Token désactivé."}, status=status.HTTP_200_OK)


class NotificationViewSet(viewsets.ReadOnlyModelViewSet):
    """Historique des notifications reçues par l'utilisateur.

    - GET /notifications/ : liste ses notifications
    - GET /notifications/{id}/ : détail
    """

    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer
    permission_classes = [permissions.IsAuthenticated, EstProprietaireNotification]

    def get_queryset(self):
        utilisateur = self.request.user
        if utilisateur.est_admin:
            return self.queryset
        return self.queryset.filter(utilisateur=utilisateur)

    @action(detail=False, methods=["get"])
    def non_lues(self, request):
        """Notifications non lues par l'utilisateur (champ `lue` = False)."""
        qs = self.get_queryset().filter(lue=False)
        serializer = self.get_serializer(qs, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"])
    def compteur(self, request):
        """Nombre de notifications non lues (badge de la cloche)."""
        nombre = Notification.objects.filter(utilisateur=request.user, lue=False).count()
        return Response({"non_lues": nombre})

    @action(detail=False, methods=["post"])
    def tout_marquer_lu(self, request):
        """Marque toutes les notifications de l'utilisateur comme lues."""
        from django.utils import timezone

        nombre = Notification.objects.filter(utilisateur=request.user, lue=False).update(
            lue=True, date_lecture=timezone.now()
        )
        return Response({"marquees": nombre})

    @action(detail=True, methods=["post"])
    def marquer_lue(self, request, pk=None):
        """Marque une notification comme lue par l'utilisateur connecté."""
        notification = self.get_object()
        notification.marquer_lue()
        serializer = self.get_serializer(notification)
        return Response(serializer.data, status=status.HTTP_200_OK)


class EnvoiNotificationView(APIView):
    """Envoi de notifications (réservé admin/système).

    - POST /notifications/envoyer/ : envoyer une notification à un utilisateur
    """

    permission_classes = [permissions.IsAuthenticated, AdminOuSystemeNotification]

    def post(self, request, *args, **kwargs):
        """Envoie une notification à un utilisateur.

        Body: {
            "utilisateur_id": <int>,
            "type_notification": "controle_ia|kyc|paiement|course_statut|litige|incident|matching|generique",
            "titre": "...",
            "corps": "...",
            "data": {}
        }
        """
        serializer = NotificationCreerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        from .models import FCMToken

        utilisateur_id = serializer.validated_data["utilisateur_id"]
        type_notification = serializer.validated_data["type_notification"]
        titre = serializer.validated_data["titre"]
        corps = serializer.validated_data["corps"]
        data = serializer.validated_data.get("data", {})

        # Vérifier que l'utilisateur existe
        from comptes.models import Utilisateur
        try:
            utilisateur = Utilisateur.objects.get(pk=utilisateur_id)
        except Utilisateur.DoesNotExist:
            return Response(
                {"detail": "Utilisateur introuvable."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Envoyer via FCM et créer historique
        success, failed = envoyer_notification_utilisateur(
            utilisateur, type_notification, titre, corps, data
        )

        return Response(
            {
                "detail": f"Notification envoyée: {success} succès, {failed} échecs.",
                "success_count": success,
                "failed_count": failed,
            },
            status=status.HTTP_200_OK,
        )