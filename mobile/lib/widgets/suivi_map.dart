import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_map/flutter_map.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:latlong2/latlong.dart';

import '../localization/app_localizations.dart';
import '../services/course_service.dart';
import '../theme/app_colors.dart';
import 'common/vehicle_icon.dart';

/// Mini carte (OpenStreetMap) : dernière position du transporteur et trajet
/// parcouru depuis le départ. Rafraîchie toutes les 30 secondes.
class SuiviMap extends ConsumerStatefulWidget {
  final String courseId;
  final String? typeVehicule;

  const SuiviMap({super.key, required this.courseId, this.typeVehicule});

  @override
  ConsumerState<SuiviMap> createState() => _SuiviMapState();
}

class _SuiviMapState extends ConsumerState<SuiviMap> {
  final _carte = MapController();
  Timer? _minuteur;
  SuiviCourse? _suivi;
  bool _carteprete = false;

  @override
  void initState() {
    super.initState();
    _charger();
    _minuteur = Timer.periodic(const Duration(seconds: 30), (_) => _charger());
  }

  @override
  void dispose() {
    _minuteur?.cancel();
    super.dispose();
  }

  Future<void> _charger() async {
    try {
      final suivi = await ref.read(courseServiceProvider).getSuivi(widget.courseId);
      if (!mounted) return;
      final anciennePosition = _suivi?.position;
      setState(() => _suivi = suivi);
      // Recentre la carte quand le transporteur a bougé.
      if (_carteprete && suivi.position != null && suivi.position != anciennePosition) {
        _carte.move(suivi.position!, _carte.camera.zoom);
      }
    } catch (_) {
      // Pas de réseau : on garde la dernière position connue.
    }
  }

  String _depuis(AppLocalizations l10n, DateTime date) {
    final minutes = DateTime.now().difference(date.toLocal()).inMinutes;
    if (minutes < 1) return l10n.positionJustNow;
    if (minutes < 60) return l10n.positionMinutesAgo(minutes.toString());
    return l10n.positionHoursAgo((minutes ~/ 60).toString());
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final suivi = _suivi;

    Widget contenu;
    if (suivi == null) {
      contenu = const Center(child: CircularProgressIndicator());
    } else if (suivi.position == null) {
      contenu = Center(
        child: Padding(
          padding: const EdgeInsets.all(24),
          child: Text(l10n.waitingFirstPosition, textAlign: TextAlign.center),
        ),
      );
    } else {
      contenu = Stack(
        children: [
          FlutterMap(
            mapController: _carte,
            options: MapOptions(
              initialCenter: suivi.position!,
              initialZoom: 13,
              onMapReady: () => _carteprete = true,
            ),
            children: [
              TileLayer(
                urlTemplate: 'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
                userAgentPackageName: 'cm.onduty.app',
              ),
              if (suivi.trace.length > 1)
                PolylineLayer(polylines: [
                  Polyline(points: suivi.trace, strokeWidth: 4, color: AppColors.primaryBrown.withValues(alpha: 0.7)),
                ]),
              MarkerLayer(markers: [
                Marker(
                  point: suivi.position!,
                  width: 48,
                  height: 48,
                  child: Container(
                    decoration: BoxDecoration(
                      color: Colors.white,
                      shape: BoxShape.circle,
                      border: Border.all(color: AppColors.primaryBrown, width: 3),
                      boxShadow: const [BoxShadow(blurRadius: 6, color: Colors.black26)],
                    ),
                    child: Icon(iconeVehicule(widget.typeVehicule), color: AppColors.primaryBrown, size: 24),
                  ),
                ),
              ]),
              const SimpleAttributionWidget(source: Text('OpenStreetMap')),
            ],
          ),
          if (suivi.dateDernierePosition != null)
            Positioned(
              left: 8,
              top: 8,
              child: Container(
                padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                decoration: BoxDecoration(
                  color: Colors.black.withValues(alpha: 0.65),
                  borderRadius: BorderRadius.circular(20),
                ),
                child: Text(
                  _depuis(l10n, suivi.dateDernierePosition!),
                  style: const TextStyle(color: Colors.white, fontSize: 12),
                ),
              ),
            ),
        ],
      );
    }

    return Card(
      clipBehavior: Clip.antiAlias,
      margin: const EdgeInsets.only(bottom: 12),
      child: SizedBox(height: 220, child: contenu),
    );
  }
}
