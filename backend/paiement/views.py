import logging

from django.db import models
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from course.models import Course
from onduty_backend.services_externes import ServiceExterneErreur, ServiceSature

from .models import Paiement, Versement
from .permissions import EstClientPaiementOuAdmin
from .serializers import PaiementInitierSerializer, PaiementSerializer
from .services import campay, escrow

logger = logging.getLogger(__name__)

STATUTS_VISIBLES_TRANSPORTEUR = (
    Paiement.StatutPaiement.BLOQUE_ESCROW,
    Paiement.StatutPaiement.LIBERE,
    Paiement.StatutPaiement.REMBOURSE,
)


def _indisponible(exc):
    logger.error("CamPay indisponible : %s", exc)
    message = (
        "Le service de paiement est très sollicité. Réessayez dans une minute."
        if isinstance(exc, ServiceSature)
        else "Le service de paiement est momentanément indisponible. Réessayez dans quelques instants."
    )
    return Response({"detail": message}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


class PaiementViewSet(viewsets.ReadOnlyModelViewSet):
    """Paiements des courses via CamPay, avec escrow.

    - GET  /paiements/                 : historique (client : ses paiements ;
                                         transporteur : les courses payées)
    - GET  /paiements/devis/?course_id= : détail du montant à payer
    - POST /paiements/?course_id=       : lance le paiement { "numero" }
    - POST /paiements/{id}/verifier/    : demande le statut à CamPay
    - POST /paiements/{id}/liberer/     : admin — verse au transporteur (litige)
    - POST /paiements/{id}/rembourser/  : admin — rembourse le client (litige)
    La libération normale se fait par la confirmation de réception de la course.
    """

    serializer_class = PaiementSerializer
    permission_classes = [permissions.IsAuthenticated, EstClientPaiementOuAdmin]

    def get_queryset(self):
        utilisateur = self.request.user
        qs = Paiement.objects.select_related(
            "course", "course__demande", "course__client", "course__transporteur"
        ).prefetch_related("versements")
        if not utilisateur.est_admin:
            qs = qs.filter(
                models.Q(course__client=utilisateur)
                | models.Q(course__transporteur=utilisateur, statut__in=STATUTS_VISIBLES_TRANSPORTEUR)
            )
        course_id = self.request.query_params.get("course_id")
        if course_id:
            qs = qs.filter(course_id=course_id)
        return qs

    def _course_du_client(self, request):
        course_id = request.query_params.get("course_id")
        if not course_id:
            return None, Response({"detail": "Paramètre 'course_id' requis."}, status=status.HTTP_400_BAD_REQUEST)
        course = Course.objects.select_related("client", "transporteur", "demande").filter(pk=course_id).first()
        if course is None or (course.client_id != request.user.id and not request.user.est_admin):
            return None, Response({"detail": "Course introuvable."}, status=status.HTTP_404_NOT_FOUND)
        return course, None

    @action(detail=False, methods=["get"])
    def devis(self, request):
        """Prix de la course + commission OnDuty + frais = total à payer."""
        course, erreur = self._course_du_client(request)
        if erreur:
            return erreur
        calcul = escrow.devis(course)
        return Response({
            **{cle: valeur for cle, valeur in calcul.items()},
            "numero_defaut": course.client.telephone,
        })

    def create(self, request, *args, **kwargs):
        """Lance le paiement : CamPay envoie une demande de validation au client."""
        course, erreur = self._course_du_client(request)
        if erreur:
            return erreur
        serializer = PaiementInitierSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            paiement = escrow.initier(course, serializer.validated_data["numero"])
        except campay.NumeroInvalide as exc:
            return Response({"numero": [str(exc)]}, status=status.HTTP_400_BAD_REQUEST)
        except (escrow.PaiementImpossible, campay.PaiementRefuse) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except ServiceExterneErreur as exc:
            return _indisponible(exc)
        return Response(
            self.get_serializer(paiement).data, status=status.HTTP_201_CREATED
        )

    @action(detail=True, methods=["post"])
    def verifier(self, request, pk=None):
        """Le client vérifie si son paiement a été validé."""
        paiement = self.get_object()
        try:
            escrow.actualiser(paiement)
        except ServiceExterneErreur as exc:
            return _indisponible(exc)
        paiement.refresh_from_db()
        return Response(self.get_serializer(paiement).data)

    def _admin_seulement(self, request):
        if not request.user.est_admin:
            return Response(
                {"detail": "Action réservée à l'administrateur."},
                status=status.HTTP_403_FORBIDDEN,
            )
        return None

    @action(detail=True, methods=["post"])
    def liberer(self, request, pk=None):
        """Admin (arbitrage d'un litige) : verse le prix au transporteur."""
        refus = self._admin_seulement(request)
        if refus:
            return refus
        paiement = self.get_object()
        if escrow.liberer(paiement) is None:
            return Response(
                {"detail": "Impossible : les fonds ne sont pas bloqués en escrow."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        paiement.refresh_from_db()
        return Response(self.get_serializer(paiement).data)

    @action(detail=True, methods=["post"])
    def rembourser(self, request, pk=None):
        """Admin (arbitrage d'un litige) : rembourse le prix au client."""
        refus = self._admin_seulement(request)
        if refus:
            return refus
        paiement = self.get_object()
        if escrow.rembourser(paiement) is None:
            return Response(
                {"detail": "Impossible : les fonds ne sont pas bloqués en escrow."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        paiement.refresh_from_db()
        return Response(self.get_serializer(paiement).data)


class CampayWebhookView(APIView):
    """Notification de CamPay à la fin d'une transaction (URL à déclarer dans
    l'application CamPay : https://<domaine>/api/paiements/campay/webhook/).

    La signature (JWT) est vérifiée, puis le statut est TOUJOURS redemandé à
    l'API CamPay : le contenu du webhook n'est jamais cru tel quel.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return self._traiter(request.query_params)

    def post(self, request):
        donnees = request.data if isinstance(request.data, dict) else {}
        return self._traiter({**request.query_params.dict(), **donnees})

    def _traiter(self, donnees):
        if not campay.signature_webhook_valide(donnees.get("signature")):
            logger.warning("Webhook CamPay rejeté : signature invalide")
            return Response(status=status.HTTP_403_FORBIDDEN)
        reference = donnees.get("reference")
        if not reference:
            return Response(status=status.HTTP_400_BAD_REQUEST)
        try:
            paiement = Paiement.objects.filter(reference_campay=reference).first()
            if paiement is not None:
                escrow.actualiser(paiement)
                return Response(status=status.HTTP_200_OK)
            versement = Versement.objects.filter(reference_campay=reference).first()
            if versement is not None:
                escrow.actualiser_versement(versement)
                return Response(status=status.HTTP_200_OK)
        except ServiceExterneErreur as exc:
            # CamPay renverra le webhook ; la commande actualiser_paiements rattrape aussi.
            logger.error("Webhook CamPay %s : vérification impossible : %s", reference, exc)
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)
        logger.warning("Webhook CamPay : référence %s inconnue", reference)
        return Response(status=status.HTTP_404_NOT_FOUND)
