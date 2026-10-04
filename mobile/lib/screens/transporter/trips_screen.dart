import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../localization/app_localizations.dart';
import '../../services/trip_service.dart';
import '../../theme/app_colors.dart';
import '../../utils/error_helper.dart';
import '../../utils/formatters.dart';
import '../../widgets/common/vehicle_icon.dart';

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
            return Card(
              margin: const EdgeInsets.only(bottom: 12),
              shape: RoundedRectangleBorder(
                borderRadius: BorderRadius.circular(16),
                side: BorderSide(color: couleur.withValues(alpha: 0.5)),
              ),
              child: ListTile(
                onTap: () => _ouvrir('/trip/${trip.id}'),
                leading: VehicleBadge(typeVehicule: trip.typeVehicule, color: couleur),
                title: Text(
                  '${trip.origin} → ${trip.destination}',
                  style: const TextStyle(fontWeight: FontWeight.w600),
                ),
                subtitle: Text(
                  '${formatDate(trip.departureDate)} · ${l10n.remainingKg(trip.capaciteRestanteKg.toStringAsFixed(0))}',
                ),
                trailing: Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: couleur.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    libelleEtatTrajet(l10n, trip.etat),
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
