import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../localization/app_localizations.dart';
import '../../../theme/app_colors.dart';
import '../../../services/shipment_service.dart';
import '../../../services/course_service.dart';
import '../../../utils/error_helper.dart';
import '../../../widgets/common/vehicle_icon.dart';

class MatchingScreen extends ConsumerStatefulWidget {
  final String shipmentId;

  const MatchingScreen({super.key, required this.shipmentId});

  @override
  ConsumerState<MatchingScreen> createState() => _MatchingScreenState();
}

class _MatchingScreenState extends ConsumerState<MatchingScreen> {
  List<MatchingItem> _matches = [];
  bool _isLoading = true;
  bool _isSelecting = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _loadMatches();
  }

  Future<void> _loadMatches() async {
    try {
      final result = await ref.read(shipmentServiceProvider).getMatching(widget.shipmentId);
      if (mounted) {
        setState(() {
          _matches = result.items;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() {
          _error = friendlyError(e);
          _isLoading = false;
        });
      }
    }
  }

  Future<void> _selectTransporter(MatchingItem match) async {
    final confirmed = await showDialog<bool>(
      context: context,
      builder: (context) => AlertDialog(
        title: Text(AppLocalizations.of(context).selectTrip),
        content: Text('Sélectionner ${match.transporter.prenom} ${match.transporter.nom} ?'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(context, false), child: const Text('Annuler')),
          FilledButton(onPressed: () => Navigator.pop(context, true), child: const Text('Confirmer')),
        ],
      ),
    );

    if (confirmed == true) {
      setState(() => _isSelecting = true);
      try {
        // `match.id` correspond à l'id du Trajet (cf. MatchingItem.fromJson).
        // Sélectionner un transporteur crée la Course : c'est SON id (et non
        // celui de la demande) qui doit être utilisé pour le paiement et le suivi.
        final course = await ref.read(courseServiceProvider).createCourse(
              demandeId: widget.shipmentId,
              trajetId: match.id,
            );
        if (mounted) {
          context.pushReplacement('/shipment/${course.id}');
        }
      } catch (e) {
        if (mounted) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(content: Text(friendlyError(e)), backgroundColor: AppColors.error),
          );
        }
      } finally {
        if (mounted) setState(() => _isSelecting = false);
      }
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
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.error_outline, size: 64, color: AppColors.error),
            const SizedBox(height: 16),
            Text(_error!),
            const SizedBox(height: 16),
            FilledButton(onPressed: () => setState(() => _loadMatches()), child: const Text('Réessayer')),
          ],
        ),
      );
    } else if (_matches.isEmpty) {
      body = Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.search_off, size: 64, color: Theme.of(context).colorScheme.primary.withValues(alpha: 0.3)),
            const SizedBox(height: 16),
            Text('Aucun transporteur disponible', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 8),
            Text('Aucun trajet ne correspond à votre demande pour le moment'),
          ],
        ),
      );
    } else {
      body = ListView.builder(
        padding: const EdgeInsets.all(16),
        itemCount: _matches.length,
        itemBuilder: (context, index) {
          final match = _matches[index];
          return _TransporterCard(match: match, onTap: () => _selectTransporter(match));
        },
      );
    }

    return Scaffold(
      appBar: AppBar(title: Text(l10n.matchingFound)),
      body: Stack(
        children: [
          body,
          if (_isSelecting)
            Container(
              color: Colors.black26,
              child: const Center(child: CircularProgressIndicator()),
            ),
        ],
      ),
    );
  }
}

class _TransporterCard extends StatelessWidget {
  final MatchingItem match;
  final VoidCallback onTap;

  const _TransporterCard({required this.match, required this.onTap});

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 12),
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                children: [
                  VehicleBadge(typeVehicule: match.typeVehicule, color: AppColors.primaryBrown, size: 56),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${match.transporter.prenom} ${match.transporter.nom}',
                          style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600),
                        ),
                        const SizedBox(height: 4),
                        Row(
                          children: [
                            Icon(Icons.star, size: 16, color: Colors.amber),
                            const SizedBox(width: 4),
                            Text('${match.transporter.scoreFiabilite.toStringAsFixed(1)} / 100',
                                style: Theme.of(context).textTheme.bodyMedium?.copyWith(color: Colors.amber[700])),
                          ],
                        ),
                      ],
                    ),
                  ),
                  Chip(
                    label: Text('${match.score.toStringAsFixed(0)}%'),
                    backgroundColor: AppColors.primaryBrown.withValues(alpha: 0.1),
                    labelStyle: TextStyle(color: AppColors.primaryBrown, fontWeight: FontWeight.w600),
                  ),
                ],
              ),
              const SizedBox(height: 16),
              Row(
                children: [
                  Icon(Icons.location_on_outlined, size: 18, color: Theme.of(context).iconTheme.color?.withValues(alpha: 0.5)),
                  const SizedBox(width: 8),
                  Text('${match.origin} → ${match.destination}',
                      style: Theme.of(context).textTheme.bodyMedium),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Icon(Icons.calendar_today_outlined, size: 18, color: Theme.of(context).iconTheme.color?.withValues(alpha: 0.5)),
                  const SizedBox(width: 8),
                  Text('Départ: ${match.departureDate.day}/${match.departureDate.month}/${match.departureDate.year}',
                      style: Theme.of(context).textTheme.bodyMedium),
                ],
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Icon(Icons.monitor_weight_outlined, size: 18, color: Theme.of(context).iconTheme.color?.withValues(alpha: 0.5)),
                  const SizedBox(width: 8),
                  Text('Capacité dispo: ${match.availableCapacityKg.toStringAsFixed(1)} kg',
                      style: Theme.of(context).textTheme.bodyMedium),
                ],
              ),
              const SizedBox(height: 16),
              SizedBox(
                width: double.infinity,
                child: FilledButton(
                  onPressed: onTap,
                  child: const Text('Sélectionner ce transporteur'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}