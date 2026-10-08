from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.utils.html import format_html
from django.contrib.admin import SimpleListFilter

from .models import Utilisateur


class TypeCompteFilter(SimpleListFilter):
    title = "Type de compte"
    parameter_name = "type_compte"

    def lookups(self, request, model_admin):
        return Utilisateur.TypeCompte.choices

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(type_compte=self.value())


@admin.action(description="Suspendre les comptes sélectionnés")
def suspendre_comptes(modeladmin, request, queryset):
    # Bloqué = aussi désactivé : la connexion et les jetons déjà émis sont refusés.
    count = queryset.exclude(type_compte=Utilisateur.TypeCompte.ADMIN).update(
        statut_compte=Utilisateur.StatutCompte.SUSPENDU, is_active=False
    )
    modeladmin.message_user(request, f"{count} compte(s) suspendu(s).")


@admin.action(description="Réactiver les comptes sélectionnés")
def reactiver_comptes(modeladmin, request, queryset):
    count = queryset.update(statut_compte=Utilisateur.StatutCompte.ACTIF, is_active=True)
    modeladmin.message_user(request, f"{count} compte(s) réactivé(s).")


@admin.action(description="Activer le rôle transporteur")
def activer_role_transporteur(modeladmin, request, queryset):
    count = queryset.update(est_transporteur=True)
    modeladmin.message_user(request, f"Rôle transporteur activé pour {count} utilisateur(s).")


@admin.action(description="Désactiver le rôle transporteur")
def desactiver_role_transporteur(modeladmin, request, queryset):
    count = queryset.update(est_transporteur=False)
    modeladmin.message_user(request, f"Rôle transporteur désactivé pour {count} utilisateur(s).")


@admin.register(Utilisateur)
class UtilisateurAdmin(UserAdmin):
    """Interface admin du modèle Utilisateur OnDuty."""

    # Affichage des colonnes dans la liste
    list_display = (
        "id",
        "telephone",
        "nom",
        "prenom",
        "email",
        "est_transporteur",
        "type_compte",
        "statut_compte",
        "score_fiabilite",
        "date_creation",
    )
    list_filter = (
        "est_transporteur",
        "type_compte",
        "statut_compte",
        "is_staff",
        TypeCompteFilter,
    )

    # Champs affichés dans les formulaires d'ajout / modification
    fieldsets = (
        (None, {"fields": ("telephone", "password")}),
        (
            "Informations personnelles",
            {"fields": ("prenom", "nom", "email", "photo_profil")},
        ),
        (
            "Rôles et statut",
            {
                "fields": (
                    "est_transporteur",
                    "type_compte",
                    "statut_compte",
                    "score_fiabilite",
                )
            },
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Dates importantes", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "telephone",
                    "prenom",
                    "nom",
                    "password1",
                    "password2",
                ),
            },
        ),
    )

    search_fields = ("telephone", "prenom", "nom", "email")
    ordering = ("id",)
    filter_horizontal = ("groups", "user_permissions")
    list_editable = ("est_transporteur", "type_compte", "statut_compte")
    list_display_links = ("id", "telephone")
    list_per_page = 50
    actions = [
        suspendre_comptes,
        reactiver_comptes,
        activer_role_transporteur,
        desactiver_role_transporteur,
    ]
    date_hierarchy = "date_creation"