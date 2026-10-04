import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../localization/app_localizations.dart';
import '../../theme/app_colors.dart';
import '../../widgets/common/primary_button.dart';
import '../../widgets/common/secondary_button.dart';

/// Confirmation que la demande a passé le contrôle IA (« la douane »),
/// avant de proposer les trajets compatibles.
class AiSuccessScreen extends StatelessWidget {
  final String demandeId;

  const AiSuccessScreen({super.key, required this.demandeId});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      body: SafeArea(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Container(
                width: 120,
                height: 120,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: AppColors.success.withValues(alpha: 0.12),
                  shape: BoxShape.circle,
                ),
                child: const Icon(Icons.verified, size: 72, color: AppColors.success),
              ),
              const SizedBox(height: 32),
              Text(
                l10n.aiSuccessTitle,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700),
              ),
              const SizedBox(height: 12),
              Text(
                l10n.aiSuccessBody,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodyLarge,
              ),
              const SizedBox(height: 40),
              PrimaryButton(
                text: l10n.aiSuccessSeeTrips,
                onPressed: () => context.pushReplacement('/matching/$demandeId'),
              ),
              const SizedBox(height: 12),
              SecondaryButton(
                text: l10n.aiSuccessWait,
                onPressed: () => context.go('/home'),
              ),
              const SizedBox(height: 12),
              Text(
                l10n.aiSuccessWaitHint,
                textAlign: TextAlign.center,
                style: Theme.of(context).textTheme.bodySmall,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
