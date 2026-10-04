import 'package:flutter/material.dart';

import '../localization/app_localizations.dart';
import '../theme/app_colors.dart';

/// 12500 → « 12 500 FCFA ».
String formatFcfa(num? montant) {
  if (montant == null) return '— FCFA';
  final entier = montant.round().toString();
  final groupes = <String>[];
  for (var i = entier.length; i > 0; i -= 3) {
    groupes.insert(0, entier.substring(i - 3 < 0 ? 0 : i - 3, i));
  }
  return '${groupes.join(' ')} FCFA';
}

String formatDate(DateTime? date) {
  if (date == null) return '';
  final local = date.toLocal();
  return '${local.day.toString().padLeft(2, '0')}/${local.month.toString().padLeft(2, '0')}/${local.year}';
}

String formatDateHeure(DateTime? date) {
  if (date == null) return '';
  final local = date.toLocal();
  return '${formatDate(local)} ${local.hour.toString().padLeft(2, '0')}:${local.minute.toString().padLeft(2, '0')}';
}

/// Libellé d'un statut de course, adapté à la place de l'utilisateur.
String libelleStatutCourse(AppLocalizations l10n, String statut, {String? role}) {
  final transporteur = role == 'transporteur';
  switch (statut) {
    case 'reservee':
      return transporteur ? l10n.courseAwaitingYourDecision : l10n.courseAwaitingTransporter;
    case 'proposition_montant':
      return transporteur ? l10n.courseProposalSent : l10n.courseProposalReceived;
    case 'en_attente_paiement':
      return l10n.courseAwaitingPayment;
    case 'payee':
      return l10n.coursePaid;
    case 'depart':
      return l10n.courseDeparted;
    case 'en_route':
      return l10n.courseOnTheWay;
    case 'arrivee':
      return l10n.courseArrived;
    case 'livree':
      return l10n.courseDelivered;
    case 'annulee':
      return l10n.courseCancelled;
    case 'en_litige':
      return l10n.courseInDispute;
    default:
      return statut;
  }
}

Color couleurStatutCourse(String statut) {
  switch (statut) {
    case 'livree':
      return AppColors.success;
    case 'annulee':
      return Colors.grey;
    case 'en_litige':
      return AppColors.error;
    case 'reservee':
    case 'proposition_montant':
    case 'en_attente_paiement':
      return AppColors.warning;
    default:
      return AppColors.primaryBrown;
  }
}

/// État d'un trajet : vert = actif (date à venir), orange = en cours
/// (aujourd'hui), rouge = passé.
Color couleurEtatTrajet(String etat) {
  switch (etat) {
    case 'actif':
      return AppColors.success;
    case 'en_cours':
      return Colors.orange;
    case 'passe':
      return AppColors.error;
    default:
      return Colors.grey;
  }
}

String libelleEtatTrajet(AppLocalizations l10n, String etat) {
  switch (etat) {
    case 'actif':
      return l10n.tripActive;
    case 'en_cours':
      return l10n.tripInProgress;
    case 'passe':
      return l10n.tripPast;
    case 'complet':
      return l10n.tripFull;
    default:
      return etat;
  }
}
