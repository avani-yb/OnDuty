import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../localization/app_localizations.dart';
import '../services/shipment_service.dart';
import '../theme/app_colors.dart';
import '../utils/error_helper.dart';

/// Rejet du contrôle IA : affiche le motif et propose de corriger la demande
/// ou de contester le rejet (revue manuelle par l'administrateur, BF-08).
/// Retourne true si une contestation a été envoyée.
Future<bool> afficherRejetIA(
  BuildContext context,
  WidgetRef ref, {
  required String demandeId,
  String? motif,
}) async {
  final l10n = AppLocalizations.of(context);
  final contester = await showDialog<bool>(
    context: context,
    builder: (dialogContext) => AlertDialog(
      title: Text(l10n.aiRejectedTitle),
      content: Text('${motif ?? ''}\n\n${l10n.aiRejectedHint}\n\n${l10n.contestHint}'.trim()),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(dialogContext).pop(true),
          child: Text(l10n.contestRejection),
        ),
        FilledButton(
          onPressed: () => Navigator.of(dialogContext).pop(false),
          child: Text(l10n.ok),
        ),
      ],
    ),
  );
  if (contester != true || !context.mounted) return false;
  return envoyerContestation(context, ref, demandeId);
}

/// Envoie la contestation et informe l'utilisateur du résultat.
Future<bool> envoyerContestation(BuildContext context, WidgetRef ref, String demandeId) async {
  final l10n = AppLocalizations.of(context);
  try {
    await ref.read(shipmentServiceProvider).contester(demandeId);
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(l10n.contestSent), backgroundColor: AppColors.success),
      );
    }
    return true;
  } catch (e) {
    if (context.mounted) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(friendlyError(e)), backgroundColor: AppColors.error),
      );
    }
    return false;
  }
}
