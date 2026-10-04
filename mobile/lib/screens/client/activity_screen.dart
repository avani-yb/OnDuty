import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../localization/app_localizations.dart';
import '../../services/course_service.dart';
import '../../services/shipment_service.dart';
import '../../theme/app_colors.dart';
import '../../utils/error_helper.dart';
import '../../utils/formatters.dart';
import '../../widgets/common/vehicle_icon.dart';

/// Activité : les courses (comme expéditeur, transporteur ou destinataire)
/// et la liste de mes demandes d'expédition.
class ActivityScreen extends ConsumerStatefulWidget {
  const ActivityScreen({super.key});

  @override
  ConsumerState<ActivityScreen> createState() => _ActivityScreenState();
}

class _ActivityScreenState extends ConsumerState<ActivityScreen> {
  List<Course> _courses = [];
  List<Shipment> _demandes = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final resultats = await Future.wait([
        ref.read(courseServiceProvider).getMyCourses(),
        ref.read(shipmentServiceProvider).getMyShipments(),
      ]);
      if (mounted) {
        setState(() {
          _courses = resultats[0] as List<Course>;
          _demandes = resultats[1] as List<Shipment>;
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

    return DefaultTabController(
      length: 2,
      child: Scaffold(
        appBar: AppBar(
          title: Text(l10n.activity),
          bottom: TabBar(tabs: [Tab(text: l10n.tabCourses), Tab(text: l10n.tabMyRequests)]),
        ),
        body: _isLoading
            ? const Center(child: CircularProgressIndicator())
            : _error != null
                ? Center(child: Text(_error!))
                : TabBarView(children: [_listeCourses(l10n), _listeDemandes(l10n)]),
      ),
    );
  }

  Widget _vide(String texte) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      children: [
        const SizedBox(height: 120),
        Icon(Icons.history, size: 80, color: AppColors.primaryBrown.withValues(alpha: 0.3)),
        const SizedBox(height: 16),
        Text(texte, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyLarge),
      ],
    );
  }

  String _libelleRole(AppLocalizations l10n, String? role) {
    switch (role) {
      case 'transporteur':
        return l10n.roleCarrier;
      case 'destinataire':
        return l10n.roleRecipient;
      default:
        return l10n.roleSender;
    }
  }

  Widget _listeCourses(AppLocalizations l10n) {
    return RefreshIndicator(
      onRefresh: _load,
      child: _courses.isEmpty
          ? _vide(l10n.noCoursesYet)
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _courses.length,
              itemBuilder: (context, index) {
                final course = _courses[index];
                final couleur = couleurStatutCourse(course.statut);
                final autre = course.estTransporteur ? course.client : course.transporteur;
                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: ListTile(
                    onTap: () => _ouvrir('/shipment/${course.id}'),
                    leading: VehicleBadge(typeVehicule: course.typeVehicule, color: couleur),
                    title: Text(
                      '${course.demande['origine'] ?? ''} → ${course.demande['destination'] ?? ''}',
                      style: const TextStyle(fontWeight: FontWeight.w600),
                    ),
                    subtitle: Text(
                      '${_libelleRole(l10n, course.role)} · ${autre['prenom'] ?? ''} ${autre['nom'] ?? ''}',
                    ),
                    trailing: _Pastille(texte: libelleStatutCourse(l10n, course.statut, role: course.role), couleur: couleur),
                  ),
                );
              },
            ),
    );
  }

  Widget _listeDemandes(AppLocalizations l10n) {
    return RefreshIndicator(
      onRefresh: _load,
      child: _demandes.isEmpty
          ? _vide(l10n.noRequestsYet)
          : ListView.builder(
              padding: const EdgeInsets.all(16),
              itemCount: _demandes.length,
              itemBuilder: (context, index) {
                final demande = _demandes[index];
                final (texte, couleur) = libelleStatutDemande(l10n, demande);
                return Card(
                  margin: const EdgeInsets.only(bottom: 12),
                  child: ListTile(
                    onTap: () => _ouvrir('/demande/${demande.id}'),
                    leading: CircleAvatar(
                      backgroundColor: couleur.withValues(alpha: 0.12),
                      child: Icon(Icons.inventory_2_outlined, color: couleur),
                    ),
                    title: Text('${demande.origin} → ${demande.destination}',
                        style: const TextStyle(fontWeight: FontWeight.w600)),
                    subtitle: Text('${formatDate(demande.preferredDate)} · ${demande.weightKg} kg · ${formatFcfa(demande.montantPropose)}'),
                    trailing: _Pastille(texte: texte, couleur: couleur),
                  ),
                );
              },
            ),
    );
  }
}

/// Libellé et couleur de l'état d'une demande.
(String, Color) libelleStatutDemande(AppLocalizations l10n, Shipment demande) {
  if (demande.aUneCourse) return (l10n.requestHasCourse, AppColors.primaryBrown);
  switch (demande.status) {
    case 'publiee':
      return (l10n.requestPublished, AppColors.success);
    case 'rejetee':
      final contestation = demande.dernierControle?['contestation'];
      if (contestation == 'en_attente') return (l10n.requestContested, AppColors.warning);
      return (l10n.requestRejected, AppColors.error);
    default:
      return (l10n.requestUnderReview, AppColors.warning);
  }
}

class _Pastille extends StatelessWidget {
  final String texte;
  final Color couleur;

  const _Pastille({required this.texte, required this.couleur});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: couleur.withValues(alpha: 0.1),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(texte, style: TextStyle(color: couleur, fontWeight: FontWeight.w600, fontSize: 11)),
    );
  }
}
