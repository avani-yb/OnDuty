"""Site d'administration OnDuty (/gestion/) — pages web réservées au compte admin.

- tableau de bord : chiffres clés et courses en cours ;
- utilisateurs : consulter, bloquer, débloquer, supprimer (ou anonymiser) ;
- litiges : fiche d'arbitrage avec toute la course, décision de l'admin ;
- fiche course : demande, contrôle IA, paiement, versements, incidents, GPS.

L'admin Django (/admin/) reste disponible en secours technique.
"""

from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.core.paginator import Paginator
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from comptes import services as comptes_services
from comptes.models import Utilisateur
from course.models import Course, PositionTransporteur
from demande.models import Demande
from litige import services as litige_services
from litige.models import Litige
from paiement.models import Paiement
from trajet.models import Trajet

STATUTS_COURSE_TERMINEE = (Course.StatutCourse.LIVREE, Course.StatutCourse.ANNULEE)
STATUTS_PAIEMENT_ENCAISSE = (
    Paiement.StatutPaiement.BLOQUE_ESCROW,
    Paiement.StatutPaiement.LIBERE,
    Paiement.StatutPaiement.REMBOURSE,
)


def admin_requis(vue):
    """Accès réservé au compte administrateur (connexion par session)."""

    @wraps(vue)
    def enveloppe(request, *args, **kwargs):
        if not request.user.is_authenticated or not getattr(request.user, "est_admin", False):
            return redirect(f"{reverse('gestion:connexion')}?{urlencode({'suivant': request.get_full_path()})}")
        return vue(request, *args, **kwargs)

    return enveloppe


# --- Connexion -----------------------------------------------------------

def connexion(request):
    suivant = request.GET.get("suivant") or request.POST.get("suivant") or reverse("gestion:tableau_de_bord")
    if not url_has_allowed_host_and_scheme(suivant, allowed_hosts={request.get_host()}):
        suivant = reverse("gestion:tableau_de_bord")
    if request.user.is_authenticated and getattr(request.user, "est_admin", False):
        return redirect(suivant)

    erreur = None
    if request.method == "POST":
        telephone = "".join(c for c in request.POST.get("telephone", "") if c.isdigit())
        utilisateur = authenticate(request, username=telephone, password=request.POST.get("mot_de_passe", ""))
        if utilisateur is not None and utilisateur.est_admin:
            login(request, utilisateur)
            return redirect(suivant)
        erreur = "Identifiants incorrects ou compte non administrateur."
    return render(request, "gestion/connexion.html", {"erreur": erreur, "suivant": suivant})


@require_POST
def deconnexion(request):
    logout(request)
    return redirect("gestion:connexion")


# --- Tableau de bord -------------------------------------------------------

@admin_requis
def tableau_de_bord(request):
    utilisateurs = Utilisateur.objects.exclude(type_compte=Utilisateur.TypeCompte.ADMIN).exclude(
        telephone__startswith="supprime-"
    )
    courses = Course.objects.all()
    paiements_encaisses = Paiement.objects.filter(statut__in=STATUTS_PAIEMENT_ENCAISSE)
    chiffres = {
        "demandes": Demande.objects.exclude(statut=Demande.StatutDemande.SUPPRIMEE).count(),
        "demandes_publiees": Demande.objects.filter(statut=Demande.StatutDemande.PUBLIEE).count(),
        "demandes_rejetees": Demande.objects.filter(statut=Demande.StatutDemande.REJETEE).count(),
        "clients": utilisateurs.count(),
        "transporteurs": utilisateurs.filter(est_transporteur=True).count(),
        "comptes_bloques": utilisateurs.filter(statut_compte=Utilisateur.StatutCompte.SUSPENDU).count(),
        "trajets_actifs": Trajet.objects.filter(statut=Trajet.StatutTrajet.ACTIF).count(),
        "courses_en_cours": courses.exclude(statut__in=STATUTS_COURSE_TERMINEE).count(),
        "courses_livrees": courses.filter(statut=Course.StatutCourse.LIVREE).count(),
        "courses_annulees": courses.filter(statut=Course.StatutCourse.ANNULEE).count(),
        "litiges_ouverts": Litige.objects.filter(statut__in=litige_services.STATUTS_OUVERTS).count(),
        "escrow": Paiement.objects.filter(statut=Paiement.StatutPaiement.BLOQUE_ESCROW).aggregate(
            total=Sum("montant_course"))["total"] or 0,
        "commissions": paiements_encaisses.aggregate(total=Sum("commission"))["total"] or 0,
        "volume_paye": paiements_encaisses.aggregate(total=Sum("montant"))["total"] or 0,
    }
    courses_en_cours = (
        courses.exclude(statut__in=STATUTS_COURSE_TERMINEE)
        .select_related("demande", "client", "transporteur")
        .order_by("-date_creation")[:50]
    )
    return render(request, "gestion/tableau_de_bord.html", {
        "chiffres": chiffres,
        "courses_en_cours": courses_en_cours,
        "menu": "tableau",
    })


# --- Utilisateurs ----------------------------------------------------------

@admin_requis
def utilisateurs(request):
    qs = Utilisateur.objects.exclude(type_compte=Utilisateur.TypeCompte.ADMIN).order_by("-date_creation")
    recherche = request.GET.get("q", "").strip()
    if recherche:
        qs = qs.filter(
            Q(nom__icontains=recherche) | Q(prenom__icontains=recherche)
            | Q(telephone__icontains=recherche) | Q(email__icontains=recherche)
        )
    filtre = request.GET.get("filtre", "tous")
    if filtre == "transporteurs":
        qs = qs.filter(est_transporteur=True)
    elif filtre == "clients":
        qs = qs.filter(est_transporteur=False)
    elif filtre == "bloques":
        qs = qs.filter(statut_compte=Utilisateur.StatutCompte.SUSPENDU)
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "gestion/utilisateurs.html", {
        "page": page,
        "recherche": recherche,
        "filtre": filtre,
        "menu": "utilisateurs",
    })


@admin_requis
def utilisateur_detail(request, pk):
    utilisateur = get_object_or_404(Utilisateur, pk=pk)
    courses = (
        Course.objects.filter(Q(client=utilisateur) | Q(transporteur=utilisateur))
        .select_related("demande", "client", "transporteur")
        .order_by("-date_creation")
    )
    statistiques = {
        "demandes": utilisateur.demandes.exclude(statut=Demande.StatutDemande.SUPPRIMEE).count(),
        "trajets": utilisateur.trajets.exclude(statut=Trajet.StatutTrajet.SUPPRIME).count(),
        "courses_client": courses.filter(client=utilisateur).count(),
        "courses_transporteur": courses.filter(transporteur=utilisateur).count(),
        "litiges": utilisateur.litiges_declares.count(),
    }
    return render(request, "gestion/utilisateur_detail.html", {
        "u": utilisateur,
        "courses": courses[:20],
        "statistiques": statistiques,
        "vehicule": getattr(utilisateur, "informations_vehicule", None),
        "kyc": utilisateur.verifications.order_by("-date_soumission").first(),
        "supprime": utilisateur.telephone.startswith("supprime-"),
        "courses_en_cours": comptes_services.courses_en_cours(utilisateur).count(),
        "historique": comptes_services.a_un_historique(utilisateur),
        "menu": "utilisateurs",
    })


@admin_requis
@require_POST
def utilisateur_action(request, pk, action):
    utilisateur = get_object_or_404(Utilisateur, pk=pk)
    nom = f"{utilisateur.prenom} {utilisateur.nom}"
    try:
        if action == "bloquer":
            comptes_services.bloquer(utilisateur, request.user)
            messages.success(request, f"Le compte de {nom} est bloqué : il ne peut plus se connecter.")
        elif action == "debloquer":
            comptes_services.debloquer(utilisateur, request.user)
            messages.success(request, f"Le compte de {nom} est débloqué.")
        elif action == "supprimer":
            if request.POST.get("confirmation") != utilisateur.telephone:
                messages.error(request, "Confirmation incorrecte : recopiez exactement le numéro de téléphone.")
                return redirect("gestion:utilisateur", pk=pk)
            resultat = comptes_services.supprimer(utilisateur, request.user)
            if resultat == "supprime":
                messages.success(request, f"Le compte de {nom} a été supprimé.")
                return redirect("gestion:utilisateurs")
            messages.success(request, f"Le compte de {nom} est fermé et anonymisé ; son historique est conservé.")
        else:
            messages.error(request, "Action inconnue.")
    except comptes_services.ActionCompteImpossible as exc:
        messages.error(request, str(exc))
    return redirect("gestion:utilisateur", pk=pk)


# --- Litiges et courses ----------------------------------------------------

@admin_requis
def litiges(request):
    qs = Litige.objects.select_related("course", "course__demande", "declarant").order_by("-date_declaration")
    filtre = request.GET.get("filtre", "a_traiter")
    if filtre == "a_traiter":
        qs = qs.filter(statut__in=litige_services.STATUTS_OUVERTS)
    elif filtre == "resolus":
        qs = qs.filter(statut=Litige.StatutLitige.RESOLU)
    page = Paginator(qs, 25).get_page(request.GET.get("page"))
    return render(request, "gestion/litiges.html", {"page": page, "filtre": filtre, "menu": "litiges"})


def _contexte_course(course):
    """Tout ce qu'il faut pour arbitrer une course, sur une seule page."""
    controle = course.demande.controles.order_by("-numero_tentative").first()
    positions = list(
        PositionTransporteur.objects.filter(course=course).order_by("date").values_list("latitude", "longitude", "date")
    )
    paiement = getattr(course, "paiement", None)
    return {
        "course": course,
        "demande": course.demande,
        "controle": controle,
        "details_visuels": (controle.resultat_coherence or {}).get("détails_visuels") if controle else None,
        "paiement": paiement,
        "versements": paiement.versements.order_by("date_creation") if paiement else [],
        "incidents": course.incidents.order_by("date_signalement"),
        "litiges_course": course.litiges.select_related("declarant").order_by("date_declaration"),
        "trace": [[float(lat), float(lng)] for lat, lng, _ in positions],
        "derniere_position": positions[-1] if positions else None,
    }


@admin_requis
def litige_detail(request, pk):
    litige = get_object_or_404(
        Litige.objects.select_related("course", "course__demande", "course__client", "course__transporteur", "declarant"),
        pk=pk,
    )
    contexte = _contexte_course(litige.course)
    contexte.update({"litige": litige, "menu": "litiges", "ouvert": litige.statut in litige_services.STATUTS_OUVERTS})
    return render(request, "gestion/litige_detail.html", contexte)


@admin_requis
@require_POST
def litige_action(request, pk, action):
    litige = get_object_or_404(Litige.objects.select_related("course"), pk=pk)
    commentaire = request.POST.get("commentaire", "")
    try:
        if action == "prendre_en_charge":
            litige_services.prendre_en_charge(litige, request.user)
            messages.success(request, "Litige pris en charge.")
        elif action == "valider_livraison":
            litige_services.valider_livraison(litige, request.user, commentaire)
            messages.success(request, "Litige résolu : livraison validée, le prix est versé au transporteur.")
        elif action == "rembourser":
            litige_services.rembourser_client(litige, request.user, commentaire)
            messages.success(request, "Litige résolu : course annulée, le prix est remboursé au client.")
        else:
            messages.error(request, "Action inconnue.")
    except litige_services.ArbitrageImpossible as exc:
        messages.error(request, str(exc))
    return redirect("gestion:litige", pk=pk)


@admin_requis
def course_detail(request, pk):
    course = get_object_or_404(
        Course.objects.select_related("demande", "client", "transporteur", "trajet"), pk=pk
    )
    contexte = _contexte_course(course)
    contexte["menu"] = "tableau"
    return render(request, "gestion/course_detail.html", contexte)


def compteurs_menu(request):
    """Processeur de contexte : nombre de litiges à traiter dans le menu."""
    if not request.path.startswith("/gestion/") or not getattr(request.user, "est_admin", False):
        return {}
    return {"nb_litiges_a_traiter": Litige.objects.filter(statut__in=litige_services.STATUTS_OUVERTS).count()}

