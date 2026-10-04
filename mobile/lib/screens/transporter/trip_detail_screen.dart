import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../localization/app_localizations.dart';
import '../../services/trip_service.dart';
import '../../theme/app_colors.dart';
import '../../utils/error_helper.dart';
import '../../utils/formatters.dart';
import '../../widgets/common/vehicle_icon.dart';

/// Détail d'un trajet. Sur un trajet « actif » uniquement :
/// - modifier (tout si aucune course, sinon la capacité seulement) ;
/// - voir les demandes compatibles, s'il reste de la capacité ;
/// - supprimer (les courses sont annulées, les clients remboursés et notifiés,
///   et la note de fiabilité baisse de 5 points par course annulée).
class TripDetailScreen extends ConsumerStatefulWidget {
  final String tripId;

  const TripDetailScreen({super.key, required this.tripId});

  @override
  ConsumerState<TripDetailScreen> createState() => _TripDetailScreenState();
}

class _TripDetailScreenState extends ConsumerState<TripDetailScreen> {
  Trip? _trip;
  bool _isLoading = true;
  bool _isActing = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final trip = await ref.read(tripServiceProvider).getTrip(widget.tripId);
      if (mounted) setState(() => _trip = trip);
    } catch (e) {
      _message(friendlyError(e), erreur: true);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _message(String texte, {bool erreur = false}) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(texte), backgroundColor: erreur ? AppColors.error : AppColors.success),
    );
  }

  Future<void> _ouvrir(String route) async {
    await context.push(route);
    if (mounted) _load();
  }

  List<Map<String, dynamic>> get _coursesActives => (_trip?.courses ?? [])
      .map((c) => Map<String, dynamic>.from(c as Map))
      .where((c) => c['statut'] != 'annulee')
      .toList();

  Future<void> _supprimer() async {
    final l10n = AppLocalizations.of(context);
    final nombre = _coursesActives.where((c) => !['livree', 'en_litige'].contains(c['statut'])).length;
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(l10n.deleteTripTitle),
        content: Text(nombre == 0 ? l10n.deleteTripBodyEmpty : l10n.deleteTripBodyWithCourses(nombre.toString(), (nombre * 5).toString())),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(l10n.cancel)),
          FilledButton(
            style: FilledButton.styleFrom(backgroundColor: AppColors.error),
            onPressed: () => Navigator.pop(c, true),
            child: Text(l10n.delete),
          ),
        ],
      ),
    );
    if (ok != true) return;

    setState(() => _isActing = true);
    try {
      final annulees = await ref.read(tripServiceProvider).deleteTrip(widget.tripId);
      _message(annulees == 0 ? l10n.tripDeleted : l10n.tripDeletedWithCourses(annulees.toString()));
      if (mounted) context.pop();
    } catch (e) {
      _message(friendlyError(e), erreur: true);
    } finally {
      if (mounted) setState(() => _isActing = false);
    }
  }

  Future<void> _modifier() async {
    final trip = _trip!;
    final champs = await showDialog<Map<String, dynamic>>(
      context: context,
      builder: (c) => _DialogueModification(trip: trip),
    );
    if (champs == null || champs.isEmpty) return;
    setState(() => _isActing = true);
    try {
      final mis = await ref.read(tripServiceProvider).updateTrip(trip.id, champs);
      if (mounted) setState(() => _trip = mis);
      if (mounted) _message(AppLocalizations.of(context).tripUpdated);
    } catch (e) {
      _message(friendlyError(e), erreur: true);
    } finally {
      if (mounted) setState(() => _isActing = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final trip = _trip;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.tripDetailTitle)),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : trip == null
              ? Center(child: Text(l10n.error))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(16),
                    children: [
                      _resume(l10n, trip),
                      const SizedBox(height: 8),
                      if (trip.estModifiable) ..._actions(l10n, trip),
                      if (!trip.estModifiable)
                        Padding(
                          padding: const EdgeInsets.symmetric(vertical: 8),
                          child: Text(l10n.tripNotEditable, style: Theme.of(context).textTheme.bodySmall),
                        ),
                      const SizedBox(height: 8),
                      Text(l10n.tripCourses, style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 8),
                      if ((trip.courses ?? []).isEmpty)
                        Text(l10n.noCourseOnTrip)
                      else
                        ...trip.courses!.map((c) => _carteCourse(l10n, Map<String, dynamic>.from(c as Map))),
                    ],
                  ),
                ),
    );
  }

  Widget _resume(AppLocalizations l10n, Trip trip) {
    final couleur = couleurEtatTrajet(trip.etat);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                VehicleBadge(typeVehicule: trip.typeVehicule, color: couleur),
                const SizedBox(width: 12),
                Expanded(
                  child: Text('${trip.origin} → ${trip.destination}',
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600)),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: couleur.withValues(alpha: 0.12),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(libelleEtatTrajet(l10n, trip.etat),
                      style: TextStyle(color: couleur, fontWeight: FontWeight.w600)),
                ),
              ],
            ),
            const SizedBox(height: 16),
            _Ligne(l10n.departureDate, formatDateHeure(trip.departureDate)),
            _Ligne(l10n.totalCapacity, '${trip.capacityKg.toStringAsFixed(0)} kg'),
            _Ligne(l10n.bookedCapacity, '${trip.kgReserves.toStringAsFixed(0)} kg'),
            _Ligne(l10n.remainingCapacity, '${trip.capaciteRestanteKg.toStringAsFixed(0)} kg'),
          ],
        ),
      ),
    );
  }

  List<Widget> _actions(AppLocalizations l10n, Trip trip) {
    return [
      if (trip.capaciteRestanteKg > 0)
        _Bouton(
          icone: Icons.search,
          texte: l10n.compatibleRequests,
          onPressed: _isActing ? null : () => _ouvrir('/matching-trips/${trip.id}'),
        ),
      _Bouton(
        icone: Icons.edit_outlined,
        texte: l10n.editTrip,
        onPressed: _isActing ? null : _modifier,
        secondaire: true,
      ),
      _Bouton(
        icone: Icons.delete_outline,
        texte: l10n.deleteTrip,
        onPressed: _isActing ? null : _supprimer,
        secondaire: true,
        danger: true,
      ),
    ];
  }

  Widget _carteCourse(AppLocalizations l10n, Map<String, dynamic> course) {
    final statut = course['statut'] as String;
    final couleur = couleurStatutCourse(statut);
    final demande = Map<String, dynamic>.from(course['demande'] ?? {});
    final client = Map<String, dynamic>.from(course['client'] ?? {});
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        onTap: () => _ouvrir('/shipment/${course['id']}'),
        title: Text('${client['prenom'] ?? ''} ${client['nom'] ?? ''}',
            style: const TextStyle(fontWeight: FontWeight.w600)),
        subtitle: Text(
          '${demande['poids_estime_kg']} kg · ${formatFcfa(course['montant_convenu'] as num?)}'
          '${course['initiee_par'] == 'transporteur' ? ' · ${l10n.youPickedThisRequest}' : ''}',
        ),
        trailing: Container(
          padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
          decoration: BoxDecoration(
            color: couleur.withValues(alpha: 0.1),
            borderRadius: BorderRadius.circular(20),
          ),
          child: Text(
            libelleStatutCourse(l10n, statut, role: 'transporteur'),
            style: TextStyle(color: couleur, fontWeight: FontWeight.w600, fontSize: 11),
          ),
        ),
      ),
    );
  }
}

/// Modification d'un trajet : tous les champs sans course, sinon la capacité.
class _DialogueModification extends StatefulWidget {
  final Trip trip;

  const _DialogueModification({required this.trip});

  @override
  State<_DialogueModification> createState() => _DialogueModificationState();
}

class _DialogueModificationState extends State<_DialogueModification> {
  late final _origine = TextEditingController(text: widget.trip.origin);
  late final _destination = TextEditingController(text: widget.trip.destination);
  late final _capacite = TextEditingController(text: widget.trip.capacityKg.toStringAsFixed(0));
  late DateTime _date = widget.trip.departureDate.toLocal();
  String? _erreur;

  bool get _capaciteSeulement => widget.trip.aDesCourses;

  Future<void> _choisirDate() async {
    final jour = await showDatePicker(
      context: context,
      initialDate: _date,
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (jour == null || !mounted) return;
    final heure = await showTimePicker(context: context, initialTime: TimeOfDay.fromDateTime(_date));
    setState(() => _date = DateTime(jour.year, jour.month, jour.day, heure?.hour ?? _date.hour, heure?.minute ?? _date.minute));
  }

  void _valider() {
    final l10n = AppLocalizations.of(context);
    final capacite = double.tryParse(_capacite.text);
    if (capacite == null || capacite <= 0) {
      setState(() => _erreur = l10n.invalidNumber);
      return;
    }
    if (capacite < widget.trip.kgReserves) {
      setState(() => _erreur = l10n.capacityBelowBooked(widget.trip.kgReserves.toStringAsFixed(0)));
      return;
    }
    final champs = <String, dynamic>{};
    if (capacite != widget.trip.capacityKg) champs['capacite_disponible_kg'] = capacite;
    if (!_capaciteSeulement) {
      if (_origine.text.trim() != widget.trip.origin) champs['origine'] = _origine.text.trim();
      if (_destination.text.trim() != widget.trip.destination) champs['destination'] = _destination.text.trim();
      if (_date != widget.trip.departureDate.toLocal()) champs['date_depart'] = _date.toIso8601String();
    }
    Navigator.pop(context, champs);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    return AlertDialog(
      title: Text(l10n.editTrip),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            if (_capaciteSeulement)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: Text(l10n.editTripCapacityOnly, style: Theme.of(context).textTheme.bodySmall),
              ),
            if (!_capaciteSeulement) ...[
              TextField(controller: _origine, decoration: InputDecoration(labelText: l10n.origin)),
              TextField(controller: _destination, decoration: InputDecoration(labelText: l10n.destination)),
              const SizedBox(height: 8),
              ListTile(
                contentPadding: EdgeInsets.zero,
                leading: const Icon(Icons.calendar_today_outlined),
                title: Text(formatDateHeure(_date)),
                onTap: _choisirDate,
              ),
            ],
            TextField(
              controller: _capacite,
              keyboardType: TextInputType.number,
              decoration: InputDecoration(labelText: l10n.totalCapacityKg, errorText: _erreur),
            ),
          ],
        ),
      ),
      actions: [
        TextButton(onPressed: () => Navigator.pop(context), child: Text(l10n.cancel)),
        FilledButton(onPressed: _valider, child: Text(l10n.save)),
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
      padding: const EdgeInsets.only(bottom: 6),
      child: Row(
        children: [
          SizedBox(width: 140, child: Text(label, style: TextStyle(color: Theme.of(context).hintColor))),
          Expanded(child: Text(valeur, style: const TextStyle(fontWeight: FontWeight.w500))),
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
