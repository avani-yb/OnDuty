import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../localization/app_localizations.dart';
import '../../services/shipment_service.dart';
import '../../theme/app_colors.dart';
import '../../utils/error_helper.dart';
import '../../utils/formatters.dart';
import '../../widgets/ai_rejection_dialog.dart';
import 'activity_screen.dart' show libelleStatutDemande;

/// Détail d'une demande d'expédition du client : modifier, supprimer,
/// contester un rejet de l'IA, voir les trajets compatibles ou la course.
class DemandeDetailScreen extends ConsumerStatefulWidget {
  final String demandeId;

  const DemandeDetailScreen({super.key, required this.demandeId});

  @override
  ConsumerState<DemandeDetailScreen> createState() => _DemandeDetailScreenState();
}

class _DemandeDetailScreenState extends ConsumerState<DemandeDetailScreen> {
  Shipment? _demande;
  bool _isLoading = true;
  bool _isActing = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final demande = await ref.read(shipmentServiceProvider).getShipment(widget.demandeId);
      if (mounted) setState(() => _demande = demande);
    } catch (e) {
      _erreur(e);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _erreur(Object e) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(friendlyError(e)), backgroundColor: AppColors.error),
    );
  }

  Future<void> _ouvrir(String route) async {
    await context.push(route);
    if (mounted) _load();
  }

  Future<void> _supprimer() async {
    final l10n = AppLocalizations.of(context);
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(l10n.deleteRequestTitle),
        content: Text(l10n.deleteRequestBody),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(l10n.cancel)),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: Text(l10n.delete)),
        ],
      ),
    );
    if (ok != true) return;
    setState(() => _isActing = true);
    try {
      await ref.read(shipmentServiceProvider).deleteShipment(widget.demandeId);
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.requestDeleted), backgroundColor: AppColors.success),
        );
        context.pop();
      }
    } catch (e) {
      _erreur(e);
    } finally {
      if (mounted) setState(() => _isActing = false);
    }
  }

  Future<void> _contester() async {
    setState(() => _isActing = true);
    await envoyerContestation(context, ref, widget.demandeId);
    if (mounted) setState(() => _isActing = false);
    _load();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final demande = _demande;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.requestDetailTitle)),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : demande == null
              ? Center(child: Text(l10n.error))
              : RefreshIndicator(onRefresh: _load, child: _contenu(l10n, demande)),
    );
  }

  Widget _contenu(AppLocalizations l10n, Shipment demande) {
    final (statut, couleur) = libelleStatutDemande(l10n, demande);
    final controle = demande.dernierControle;
    final statutCourse = demande.courseActive?['statut'] as String?;
    final modifiable = statutCourse == null || !['livree', 'en_litige'].contains(statutCourse);

    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16),
      children: [
        Card(
          child: Padding(
            padding: const EdgeInsets.all(16),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text('${demande.origin} → ${demande.destination}',
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600)),
                    ),
                    Container(
                      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                      decoration: BoxDecoration(
                        color: couleur.withValues(alpha: 0.1),
                        borderRadius: BorderRadius.circular(20),
                      ),
                      child: Text(statut, style: TextStyle(color: couleur, fontWeight: FontWeight.w600)),
                    ),
                  ],
                ),
                const SizedBox(height: 16),
                _Ligne(l10n.date, formatDate(demande.preferredDate)),
                _Ligne(l10n.weight, '${demande.weightKg} kg'),
                _Ligne(l10n.proposedPrice, formatFcfa(demande.montantPropose)),
                _Ligne(l10n.description, demande.description),
                _Ligne(
                  l10n.recipientPhone,
                  demande.telephoneDestinataire.isEmpty ? '—' : demande.telephoneDestinataire,
                ),
                if (demande.destinataire != null)
                  Padding(
                    padding: const EdgeInsets.only(top: 4),
                    child: Text(
                      l10n.recipientIsMember('${demande.destinataire!['prenom']} ${demande.destinataire!['nom']}'),
                      style: Theme.of(context).textTheme.bodySmall?.copyWith(color: AppColors.success),
                    ),
                  ),
              ],
            ),
          ),
        ),
        if (demande.estRejetee && controle != null) ...[
          const SizedBox(height: 12),
          Card(
            color: AppColors.error.withValues(alpha: 0.06),
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(l10n.aiRejectedTitle, style: const TextStyle(fontWeight: FontWeight.w700)),
                  const SizedBox(height: 8),
                  Text((controle['motif_rejet'] as String?) ?? ''),
                  if (controle['contestation'] == 'en_attente') ...[
                    const SizedBox(height: 8),
                    Text(l10n.contestPending, style: const TextStyle(color: AppColors.warning)),
                  ],
                  if (controle['contestation'] == 'confirmee') ...[
                    const SizedBox(height: 8),
                    Text(l10n.contestConfirmed, style: const TextStyle(color: AppColors.error)),
                  ],
                ],
              ),
            ),
          ),
        ],
        const SizedBox(height: 16),
        if (demande.aUneCourse)
          _Bouton(
            icone: Icons.local_shipping_outlined,
            texte: l10n.viewCourse,
            onPressed: () => _ouvrir('/shipment/${demande.courseActive!['id']}'),
          ),
        if (demande.estPubliee && !demande.aUneCourse)
          _Bouton(
            icone: Icons.search,
            texte: l10n.viewCompatibleTrips,
            onPressed: () => _ouvrir('/matching/${demande.id}'),
          ),
        if (demande.peutContester)
          _Bouton(
            icone: Icons.gavel_outlined,
            texte: l10n.contestRejection,
            onPressed: _isActing ? null : _contester,
            secondaire: true,
          ),
        if (modifiable)
          _Bouton(
            icone: Icons.edit_outlined,
            texte: l10n.edit,
            onPressed: _isActing ? null : () => _ouvrir('/demande/${demande.id}/modifier'),
            secondaire: true,
          ),
        if (!demande.aUneCourse)
          _Bouton(
            icone: Icons.delete_outline,
            texte: l10n.delete,
            onPressed: _isActing ? null : _supprimer,
            secondaire: true,
            danger: true,
          ),
      ],
    );
  }
}

class _Ligne extends StatelessWidget {
  final String label;
  final String valeur;

  const _Ligne(this.label, this.valeur);

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 120,
            child: Text(label, style: TextStyle(color: Theme.of(context).hintColor)),
          ),
          Expanded(child: Text(valeur)),
        ],
      ),
    );
  }
}

class _Bouton extends StatelessWidget {
  final IconData icone;
  final String texte;
  final VoidCallback? onPressed;
  final bool secondaire;
  final bool danger;

  const _Bouton({
    required this.icone,
    required this.texte,
    required this.onPressed,
    this.secondaire = false,
    this.danger = false,
  });

  @override
  Widget build(BuildContext context) {
    final bouton = secondaire
        ? OutlinedButton.icon(
            onPressed: onPressed,
            icon: Icon(icone),
            label: Text(texte),
            style: danger ? OutlinedButton.styleFrom(foregroundColor: AppColors.error) : null,
          )
        : FilledButton.icon(onPressed: onPressed, icon: Icon(icone), label: Text(texte));
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: SizedBox(width: double.infinity, child: bouton),
    );
  }
}
