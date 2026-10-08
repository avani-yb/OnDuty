import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../localization/app_localizations.dart';
import '../../services/trip_service.dart';
import '../../theme/app_colors.dart';
import '../../utils/error_helper.dart';
import '../../utils/formatters.dart';
import '../../widgets/common/vehicle_card.dart';

/// Trajets du transporteur, dans l'ordre fourni par le serveur :
/// actifs (vert) puis en cours aujourd'hui (orange) puis passés (rouge).
class TripsScreen extends ConsumerStatefulWidget {
  const TripsScreen({super.key});

  @override
  ConsumerState<TripsScreen> createState() => _TripsScreenState();
}

class _TripsScreenState extends ConsumerState<TripsScreen> {
  List<Trip> _trips = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final trips = await ref.read(tripServiceProvider).getMyTrips();
      if (mounted) {
        setState(() {
          _trips = trips;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _ouvrir(String route) async {
    await context.push(route);
    if (mounted) _load();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    Widget body;
    if (_isLoading) {
      body = const Center(child: CircularProgressIndicator());
    } else if (_error != null) {
      body = Center(child: Text(_error!));
    } else if (_trips.isEmpty) {
      body = Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.local_shipping, size: 80, color: AppColors.primaryBrown.withValues(alpha: 0.3)),
            const SizedBox(height: 16),
            Text(l10n.noTripsYet, style: Theme.of(context).textTheme.bodyLarge),
          ],
        ),
      );
    } else {
      body = RefreshIndicator(
        onRefresh: _load,
        child: ListView.builder(
          padding: const EdgeInsets.all(16),
          itemCount: _trips.length,
          itemBuilder: (context, index) {
            final trip = _trips[index];
            final couleur = couleurEtatTrajet(trip.etat);
            return CarteVehicule(
              typeVehicule: trip.typeVehicule,
              couleur: couleur,
              titre: '${trip.origin} → ${trip.destination}',
              sousTitre: '${formatDate(trip.departureDate)} · ${l10n.remainingKg(trip.capaciteRestanteKg.toStringAsFixed(0))}',
              trailing: PastilleStatut(texte: libelleEtatTrajet(l10n, trip.etat), couleur: couleur),
              onTap: () => _ouvrir('/trip/${trip.id}'),
            );
          },
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(title: Text(l10n.trips)),
      body: body,
      floatingActionButton: FloatingActionButton(
        tooltip: l10n.newTrip,
        onPressed: () => _ouvrir('/new-trip'),
        child: const Icon(Icons.add),
      ),
    );
  }
}
