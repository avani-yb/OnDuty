import logging
import mimetypes

from django.db import transaction
from django.http import FileResponse, Http404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView

from onduty_backend.services_externes import ServiceExterneErreur

from .models import Verification
from .permissions import SeulAdminPeutTraiter
from .serializers import (
    TraitementVerificationSerializer,
    VerificationSerializer,
)
from .services import kyc, smile_identity

logger = logging.getLogger(__name__)

CHAMPS_DOCUMENTS = ("cni_recto", "cni_verso", "selfie")


class VerificationViewSet(viewsets.ModelViewSet):
    """Gestion des vérifications KYC/CNI.

    - Un utilisateur SOUMET une vérification (photos en multipart) et
      consulte son historique.
    - Selon KYC_FOURNISSEUR, la CNI est transmise à Smile Identity ou laissée
      à la validation manuelle de l'administrateur.
    - L'administrateur traite (valide/rejette) les vérifications.
    """

    permission_classes = [permissions.IsAuthenticated, SeulAdminPeutTraiter]

    def get_queryset(self):
        utilisateur = self.request.user
        if utilisateur.est_admin:
            return Verification.objects.all()
        return Verification.objects.filter(utilisateur=utilisateur)

    def get_serializer_class(self):
        # Dès qu'on modifie une vérification, on utilise le sérialiseur admin
        if self.action in ("update", "partial_update"):
            return TraitementVerificationSerializer
        return VerificationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        verification = None
        try:
            with transaction.atomic():
                verification = serializer.save()
                kyc.soumettre(verification)
        except ServiceExterneErreur as exc:
            # Rien n'est conservé : l'utilisateur pourra simplement renvoyer
            # ses photos (BNF-03 : erreur explicite plutôt que silence).
            logger.error("KYC : envoi au fournisseur impossible : %s", exc)
            _supprimer_fichiers(verification)
            return Response(
                {"detail": exc.message_utilisateur},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        return Response(
            VerificationSerializer(verification, context=self.get_serializer_context()).data,
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"], url_path=r"document/(?P<champ>[a-z_]+)")
    def document(self, request, pk=None, champ=None):
        """Photo d'une vérification : propriétaire ou administrateur uniquement."""
        verification = self.get_object()
        if champ not in CHAMPS_DOCUMENTS or not getattr(verification, champ):
            raise Http404
        if request.user.est_admin and verification.utilisateur_id != request.user.id:
            # Traçabilité des accès admin aux documents CNI (docs/14, section 7).
            logger.info(
                "Accès admin %s au document %s de la vérification %s",
                request.user.pk, champ, verification.pk,
            )
        fichier = getattr(verification, champ)
        type_mime = mimetypes.guess_type(fichier.name)[0] or "application/octet-stream"
        return FileResponse(fichier.open("rb"), content_type=type_mime)

    @action(detail=True, methods=["post"])
    def actualiser(self, request, pk=None):
        """Demande au fournisseur le résultat d'une vérification en attente."""
        verification = self.get_object()
        try:
            kyc.actualiser(verification)
        except ServiceExterneErreur as exc:
            logger.error("KYC %s : actualisation impossible : %s", verification.pk, exc)
            return Response(
                {"detail": exc.message_utilisateur},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )
        verification.refresh_from_db()
        return Response(VerificationSerializer(verification).data)


class SmileCallbackView(APIView):
    """Réception du résultat envoyé par Smile Identity (SMILE_CALLBACK_URL).

    Pas d'authentification JWT : l'authenticité est garantie par la
    signature HMAC du message, vérifiée avec la clé API.
    """

    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        donnees = request.data if isinstance(request.data, dict) else {}
        try:
            signature_ok = smile_identity.signature_valide(
                donnees.get("timestamp"), donnees.get("signature")
            )
        except ServiceExterneErreur:
            signature_ok = False
        if not signature_ok:
            logger.warning("Callback Smile Identity rejeté : signature invalide")
            return Response(status=status.HTTP_403_FORBIDDEN)

        job_id = (donnees.get("PartnerParams") or {}).get("job_id")
        verification = Verification.objects.filter(
            job_id_fournisseur=job_id,
            fournisseur=Verification.Fournisseur.SMILE,
        ).first() if job_id else None
        if verification is None:
            logger.warning("Callback Smile Identity : job %r inconnu", job_id)
            return Response(status=status.HTTP_404_NOT_FOUND)

        resultat = {k: v for k, v in donnees.items() if k not in ("signature", "timestamp")}
        kyc.appliquer_resultat(verification.pk, resultat)
        return Response(status=status.HTTP_200_OK)


def _supprimer_fichiers(verification):
    if verification is None:
        return
    for champ in CHAMPS_DOCUMENTS:
        fichier = getattr(verification, champ)
        if fichier:
            fichier.delete(save=False)
