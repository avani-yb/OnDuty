import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../localization/app_localizations.dart';
import '../../services/course_service.dart';
import '../../services/shipment_service.dart';
import '../../theme/app_colors.dart';
import '../../utils/error_helper.dart';
import '../../utils/formatters.dart';

/// Demandes compatibles avec un trajet. Le transporteur peut en choisir une,
/// au prix proposé par le client ou à un autre prix ; le client doit ensuite
/// accepter (puis payer) ou refuser.
class MatchingTripsScreen extends ConsumerStatefulWidget {
  final String tripId;

  const MatchingTripsScreen({super.key, required this.tripId});

  @override
  ConsumerState<MatchingTripsScreen> createState() => _MatchingTripsScreenState();
}

class _MatchingTripsScreenState extends ConsumerState<MatchingTripsScreen> {
  List<MatchingItem> _matches = [];
  bool _isLoading = true;
  bool _isActing = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final result = await ref.read(shipmentServiceProvider).getMatchingForTrip(widget.tripId);
      if (mounted) {
        setState(() {
          _matches = result.items;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _choisir(MatchingItem demande) async {
    final l10n = AppLocalizations.of(context);
    final montant = await showDialog<double>(
      context: context,
      builder: (c) => _DialogueChoix(prixClient: demande.montantPropose ?? 0),
    );
    if (montant == null) return;

    setState(() => _isActing = true);
    try {
      await ref.read(courseServiceProvider).proposer(
            demandeId: demande.id,
            trajetId: widget.tripId,
            montant: montant == demande.montantPropose ? null : montant,
          );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.requestPickedMessage), backgroundColor: AppColors.success),
        );
      }
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(friendlyError(e)), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _isActing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    Widget body;
    if (_isLoading) {
      body = const Center(child: CircularProgressIndicator());
    } else if (_error != null) {
      body = Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              const Icon(Icons.error_outline, size: 64, color: AppColors.error),
              const SizedBox(height: 16),
              Text(_error!, textAlign: TextAlign.center),
              const SizedBox(height: 16),
              FilledButton(onPressed: _load, child: Text(l10n.retry)),
            ],
          ),
        ),
      );
    } else if (_matches.isEmpty) {
      body = Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            children: [
              Icon(Icons.search_off, size: 64, color: AppColors.primaryBrown.withValues(alpha: 0.3)),
              const SizedBox(height: 16),
              Text(l10n.noCompatibleRequests, textAlign: TextAlign.center,
                  style: Theme.of(context).textTheme.titleMedium),
            ],
          ),
        ),
      );
    } else {
      body = RefreshIndicator(
        onRefresh: _load,
        child: ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: _matches.length,
          itemBuilder: (context, index) => _CarteDemande(
            demande: _matches[index],
            onChoisir: _isActing ? null : () => _choisir(_matches[index]),
          ),
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: Text(l10n.compatibleRequestsTitle)),
      body: body,
    );
  }
}

class _CarteDemande extends StatelessWidget {
  final MatchingItem demande;
  final VoidCallback? onChoisir;

  const _CarteDemande({required this.demande, required this.onChoisir});

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final details = demande.detailsVisuels;
    final resumeIA = details == null
        ? null
        : ['type', 'marque', 'couleur', 'etat', 'contenant']
            .map((cle) => details[cle])
            .where((v) => v != null && v.toString().isNotEmpty)
            .join(' · ');

    Widget ligne(IconData icone, String texte) => Padding(
          padding: const EdgeInsets.only(bottom: 6),
          child: Row(children: [
            Icon(icone, size: 18, color: Theme.of(context).hintColor),
            const SizedBox(width: 8),
            Expanded(child: Text(texte)),
          ]),
        );

    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text('${demande.origin} → ${demande.destination}',
                      style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600)),
                ),
                Text(formatFcfa(demande.montantPropose),
                    style: const TextStyle(fontWeight: FontWeight.w700, color: AppColors.primaryBrown)),
              ],
            ),
            const SizedBox(height: 12),
            ligne(Icons.calendar_today_outlined, l10n.wishedDate(formatDate(demande.preferredDate))),
            ligne(Icons.monitor_weight_outlined, '${demande.weightKg?.toStringAsFixed(1) ?? '?'} kg'),
            if ((demande.description ?? '').isNotEmpty) ligne(Icons.description_outlined, demande.description!),
            if (resumeIA != null && resumeIA.isNotEmpty) ligne(Icons.smart_toy_outlined, resumeIA),
            const SizedBox(height: 8),
            SizedBox(
              width: double.infinity,
              child: FilledButton.icon(
                onPressed: onChoisir,
                icon: const Icon(Icons.handshake_outlined),
                label: Text(l10n.pickThisRequest),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// Garder le prix du client ou en proposer un autre.
class _DialogueChoix extends StatefulWidget {
  final double prixClient;

  const _DialogueChoix({required this.prixClient});

  @override
  State<_DialogueChoix> createState() => _DialogueChoixState();
}

class _DialogueChoixState extends State<_DialogueChoix> {
  bool _autrePrix = false;
  late final _montant = TextEditingController(text: widget.prixClient.round().toString());
  String? _erreur;

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l10n.pickThisRequest),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SegmentedButton<bool>(
            segments: [
              ButtonSegment(value: false, label: Text(l10n.keepClientPrice(formatFcfa(widget.prixClient)))),
              ButtonSegment(value: true, label: Text(l10n.proposeOtherPrice)),
            ],
            selected: {_autrePrix},
            showSelectedIcon: false,
            onSelectionChanged: (choix) => setState(() => _autrePrix = choix.first),
          ),
          const SizedBox(height: 8),
          if (_autrePrix)
            TextField(
              controller: _montant,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(labelText: l10n.amountFcfa, errorText: _erreur),
            ),
          const SizedBox(height: 8),
          Text(l10n.clientMustAccept, style: Theme.of(context).textTheme.bodySmall),
        ],
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: Text(l10n.cancel)),
        FilledButton(
          onPressed: () {
            if (!_autrePrix) {
              Navigator.pop(context, widget.prixClient);
              return;
            }
            final montant = double.tryParse(_montant.text);
            if (montant == null || montant <= 0) {
              setState(() => _erreur = l10n.invalidNumber);
              return;
            }
            Navigator.pop(context, montant);
          },
          child: Text(l10n.send),
        ),
      ],
    );
  }
}
