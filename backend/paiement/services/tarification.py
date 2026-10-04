"""Calcul du montant payé par le client pour une course.

Règles (décision du 04/10/2026) :
- commission OnDuty : 5 % si le prix est inférieur ou égal à 10 000 FCFA,
  10 % au-delà ;
- frais CamPay : 2 × le taux CamPay (CAMPAY_FRAIS_POURCENT), calculés sur le
  prix de la course. Le double couvre l'encaissement ET le versement au
  transporteur, pour que la commission d'OnDuty reste intacte ;
- chaque montant est arrondi au franc supérieur (CamPay n'accepte que des
  montants entiers).
"""

from decimal import ROUND_CEILING, Decimal

from django.conf import settings

SEUIL_COMMISSION = Decimal("10000")
TAUX_COMMISSION_BAS = Decimal("0.05")
TAUX_COMMISSION_HAUT = Decimal("0.10")


def _arrondi(valeur: Decimal) -> Decimal:
    return valeur.quantize(Decimal("1"), rounding=ROUND_CEILING)


def taux_commission(prix: Decimal) -> Decimal:
    return TAUX_COMMISSION_BAS if prix <= SEUIL_COMMISSION else TAUX_COMMISSION_HAUT


def calculer(prix) -> dict:
    """Détail du paiement pour un prix de course donné."""
    prix = _arrondi(Decimal(prix))
    commission = _arrondi(prix * taux_commission(prix))
    taux_campay = Decimal(str(settings.CAMPAY_FRAIS_POURCENT)) / 100
    frais = _arrondi(2 * taux_campay * prix)
    return {
        "montant_course": prix,
        "taux_commission": taux_commission(prix) * 100,
        "commission": commission,
        "frais": frais,
        "total": prix + commission + frais,
    }
