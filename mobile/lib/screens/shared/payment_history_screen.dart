import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../localization/app_localizations.dart';
import '../../services/payment_service.dart';
import '../../theme/app_colors.dart';
import '../../utils/error_helper.dart';
import '../../utils/formatters.dart';

/// Historique des paiements. Libellés fournis par le serveur selon le rôle :
/// client « En cours / Échoué / Effectué / Remboursé », transporteur
/// « En attente de livraison / Reçu / Course annulée ».
class PaymentHistoryScreen extends ConsumerStatefulWidget {
  const PaymentHistoryScreen({super.key});

  @override
  ConsumerState<PaymentHistoryScreen> createState() => _PaymentHistoryScreenState();
}

class _PaymentHistoryScreenState extends ConsumerState<PaymentHistoryScreen> {
  List<Paiement> _paiements = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final paiements = await ref.read(paymentServiceProvider).getMyPayments();
      if (mounted) {
        setState(() {
          _paiements = paiements;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Color _couleur(Paiement p) {
    switch (p.statut) {
      case 'en_attente':
        return AppColors.warning;
      case 'echoue':
        return AppColors.error;
      case 'rembourse':
        return Colors.grey;
      case 'libere':
        return AppColors.success;
      default: // bloque_escrow
        return p.role == 'transporteur' ? AppColors.warning : AppColors.success;
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    Widget body;
    if (_isLoading) {
      body = const Center(child: CircularProgressIndicator());
    } else if (_error != null) {
      body = Center(child: Text(_error!));
    } else if (_paiements.isEmpty) {
      body = Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.receipt_long_outlined, size: 80, color: AppColors.primaryBrown.withValues(alpha: 0.3)),
            const SizedBox(height: 16),
            Text(l10n.noPaymentsYet, style: Theme.of(context).textTheme.bodyLarge),
          ],
        ),
      );
    } else {
      body = RefreshIndicator(
        onRefresh: _load,
        child: ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: _paiements.length,
          itemBuilder: (context, index) {
            final paiement = _paiements[index];
            final transporteur = paiement.role == 'transporteur';
            final couleur = _couleur(paiement);
            final autre = (transporteur ? paiement.course['client'] : paiement.course['transporteur']) as Map? ?? {};
            // Le client voit ce qu'il a payé ; le transporteur ce qu'il reçoit.
            final montant = transporteur ? paiement.montantCourse : (paiement.montant ?? paiement.montantCourse);

            return Card(
              margin: const EdgeInsets.only(bottom: 12),
              child: ListTile(
                onTap: () => context.push('/shipment/${paiement.course['id']}'),
                leading: CircleAvatar(
                  backgroundColor: (transporteur ? AppColors.success : AppColors.primaryBrown).withValues(alpha: 0.1),
                  child: Icon(
                    transporteur ? Icons.arrow_downward : Icons.arrow_upward,
                    color: transporteur ? AppColors.success : AppColors.primaryBrown,
                  ),
                ),
                title: Text(
                  '${transporteur ? '+' : '-'}${formatFcfa(montant)}',
                  style: const TextStyle(fontWeight: FontWeight.w700),
                ),
                subtitle: Text(
                  '${paiement.course['origine'] ?? ''} → ${paiement.course['destination'] ?? ''}\n'
                  '${autre['prenom'] ?? ''} ${autre['nom'] ?? ''} · ${formatDate(paiement.dateCreation)}',
                ),
                isThreeLine: true,
                trailing: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: couleur.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    paiement.statutAffiche,
                    style: TextStyle(color: couleur, fontWeight: FontWeight.w600, fontSize: 11),
                  ),
                ),
              ),
            );
          },
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: Text(l10n.paymentHistory)),
      body: body,
    );
  }
}
