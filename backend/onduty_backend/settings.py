"""
Django settings for onduty_backend project.
"""

import os
from datetime import timedelta
from pathlib import Path

from dotenv import load_dotenv

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Chargement du fichier .env (situé à la racine du backend)
load_dotenv(BASE_DIR / ".env")


# ==============================
# Clé secrète et débogage
# ==============================
SECRET_KEY = os.getenv("DJANGO_SECRET_KEY")

DEBUG = os.getenv("DJANGO_DEBUG", "False").lower() in ("true", "1", "yes")

ALLOWED_HOSTS = [
    h.strip()
    for h in os.getenv("DJANGO_ALLOWED_HOSTS", "").split(",")
    if h.strip()
]


# ==============================
# Applications installées
# ==============================
INSTALLED_APPS = [
    # Applications Django de base
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # Bibliothèques / frameworks
    "rest_framework",                  # Django REST Framework
    "rest_framework_simplejwt",        # Authentification JWT
    "corsheaders",                     # CORS (accès API depuis le mobile)
    # Applications métier OnDuty
    "comptes",
    "vehicule",
    "verification",
    "trajet",
    "demande",
    "matching",
    "course",
    "paiement",
    "litige",
    "evaluation",
    "notification",
    "administration",
]

MIDDLEWARE = [
    # CORS doit être le plus haut possible
    "corsheaders.middleware.CorsMiddleware",
    "django.middleware.security.SecurityMiddleware",
    # Sert les fichiers statiques (admin, DRF browsable API) directement
    # depuis Django : pratique sur un PaaS simple (Render/Railway) sans
    # serveur web séparé devant l'app.
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "onduty_backend.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "onduty_backend.wsgi.application"


# ==============================
# Base de données
# ==============================
DATABASES = {
    "default": {
        "ENGINE": os.getenv("DB_ENGINE", "django.db.backends.postgresql"),
        "NAME": os.getenv("DB_NAME", "onduty_local_db"),
        "USER": os.getenv("DB_USER", "onduty_user"),
        "PASSWORD": os.getenv("DB_PASSWORD", ""),
        "HOST": os.getenv("DB_HOST", "localhost"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}

# La plupart des PaaS (Render, Railway...) fournissent une seule variable
# DATABASE_URL plutôt que des DB_HOST/DB_NAME/... séparées : si elle est
# présente, elle prend le dessus sur la config ci-dessus.
_database_url = os.getenv("DATABASE_URL")
if _database_url:
    import dj_database_url

    DATABASES["default"] = dj_database_url.parse(_database_url, conn_max_age=600)


# ==============================
# Modèle utilisateur personnalisé
# ==============================
AUTH_USER_MODEL = "comptes.Utilisateur"


# ==============================
# Validation des mots de passe
# ==============================
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


# ==============================
# Django REST Framework
# ==============================
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),
    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),
    # Par défaut, DRF sérialise les DecimalField en chaînes de caractères
    # (ex. "20.00") pour préserver la précision. L'app mobile Flutter attend
    # des nombres JSON pour les poids, capacités, montants et scores — on
    # désactive donc ce comportement pour renvoyer de vrais nombres.
    "COERCE_DECIMAL_TO_STRING": False,
}

# ==============================
# Simple JWT (authentification par token)
# ==============================
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=30),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": False,
    "AUTH_HEADER_TYPES": ("Bearer",),
}


# ==============================
# CORS (accès depuis l'app mobile)
# ==============================
CORS_ALLOW_ALL_ORIGINS = DEBUG  # Autorisé en développement uniquement
CORS_ALLOWED_ORIGINS = []


# ==============================
# Internationalisation
# ==============================
LANGUAGE_CODE = "fr-fr"

TIME_ZONE = "Africa/Douala"

USE_I18N = True

USE_TZ = True


# ==============================
# Fichiers statiques et médias
# ==============================
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
    # Documents sensibles (CNI, selfies KYC) : hors de MEDIA_ROOT, donc jamais
    # servis par une URL publique. Accessibles uniquement via l'API, au
    # propriétaire et à l'admin (docs/14, section 4).
    "prive": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
        "OPTIONS": {"location": BASE_DIR / "private_media", "base_url": None},
    },
}

MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"


DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==============================
# Services externes (clés dans le .env uniquement, cf. .env.example)
# ==============================
# Une clé absente ne fait pas planter le démarrage : le service concerné lève
# `ServiceNonConfigure` au moment de l'appel.

# Contrôle IA des demandes : "simulation" ou "reel"
IA_FOURNISSEUR = os.getenv("IA_FOURNISSEUR", "simulation").strip().lower()
IA_BUDGET_SECONDES = float(os.getenv("IA_BUDGET_SECONDES") or 30)
# Détection d'objets : "groq" (défaut, sans carte bancaire) ou "google"
# (Google Cloud Vision en plus de Groq)
IA_DETECTION = os.getenv("IA_DETECTION", "groq").strip().lower()
# Nombre d'images extraites de la vidéo et analysées
IA_NB_IMAGES = int(os.getenv("IA_NB_IMAGES") or 5)

# Google Cloud Vision (le SDK lit lui-même GOOGLE_APPLICATION_CREDENTIALS)
GOOGLE_APPLICATION_CREDENTIALS = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "")
VISION_TIMEOUT_SECONDS = float(os.getenv("VISION_TIMEOUT_SECONDS") or 10)
VISION_SEUIL_CONFIANCE = float(os.getenv("VISION_SEUIL_CONFIANCE") or 0.7)

# Groq
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
# Modèle vision-langage (doit accepter les images)
GROQ_MODEL = os.getenv("GROQ_MODEL") or "qwen/qwen3.8-27b"
GROQ_TIMEOUT_SECONDS = float(os.getenv("GROQ_TIMEOUT_SECONDS") or 20)
GROQ_SEUIL_CONFIANCE = float(os.getenv("GROQ_SEUIL_CONFIANCE") or 0.6)
# Nombre maximal d'images par requête accepté par le modèle (3 pour qwen3.8-27b)
GROQ_MAX_IMAGES = int(os.getenv("GROQ_MAX_IMAGES") or 3)
# Longueur maximale de la réponse (l'offre gratuite limite les jetons de sortie par minute)
GROQ_MAX_TOKENS = int(os.getenv("GROQ_MAX_TOKENS") or 500)

# Smile Identity
SMILE_PARTNER_ID = os.getenv("SMILE_PARTNER_ID", "")
SMILE_API_KEY = os.getenv("SMILE_API_KEY", "")
SMILE_ENV = os.getenv("SMILE_ENV", "sandbox").strip().lower()
SMILE_CALLBACK_URL = os.getenv("SMILE_CALLBACK_URL", "")
SMILE_TIMEOUT_SECONDS = float(os.getenv("SMILE_TIMEOUT_SECONDS") or 20)
KYC_FOURNISSEUR = os.getenv("KYC_FOURNISSEUR", "manuel").strip().lower()

# CamPay (paiements MTN MoMo / Orange Money)
CAMPAY_USERNAME = os.getenv("CAMPAY_USERNAME", "")
CAMPAY_PASSWORD = os.getenv("CAMPAY_PASSWORD", "")
CAMPAY_WEBHOOK_KEY = os.getenv("CAMPAY_WEBHOOK_KEY", "")
# "demo" (tests, argent fictif) ou "production"
CAMPAY_ENV = os.getenv("CAMPAY_ENV", "demo").strip().lower()
CAMPAY_TIMEOUT_SECONDS = float(os.getenv("CAMPAY_TIMEOUT_SECONDS") or 20)
# Taux des frais CamPay en % (lu sur le tableau de bord CamPay) ; le client
# paie 2 × ce taux pour couvrir l'encaissement et le versement.
CAMPAY_FRAIS_POURCENT = float(os.getenv("CAMPAY_FRAIS_POURCENT") or 0)
KYC_REQUIS_TRANSPORTEUR = os.getenv(
    "KYC_REQUIS_TRANSPORTEUR", "True"
).lower() in ("true", "1", "yes")


# ==============================
# Journalisation (erreurs des services externes visibles en console)
# ==============================
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "loggers": {
        "demande": {"handlers": ["console"], "level": "INFO"},
        "verification": {"handlers": ["console"], "level": "INFO"},
    },
}
