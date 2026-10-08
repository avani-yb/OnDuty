import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../localization/app_localizations.dart';
import '../../theme/app_colors.dart';
import '../../services/auth_service.dart';
import '../../services/course_service.dart';
import '../../services/gps_service.dart';
import '../../services/push_service.dart';
import '../../services/notification_service.dart';
import '../../utils/formatters.dart';
import '../../widgets/common/vehicle_card.dart';
import 'activity_screen.dart';
import '../transporter/trips_screen.dart';
import '../shared/profile_screen.dart';

/// Coquille de navigation principale : une seule barre de navigation basse,
/// persistante, qui bascule entre les 4 onglets réels (au lieu de naviguer
/// vers de nouvelles pages à chaque tap, ce qui faisait disparaître la barre).
class HomeScreen extends ConsumerStatefulWidget {
  const HomeScreen({super.key});

  @override
  ConsumerState<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends ConsumerState<HomeScreen> {
  int _selectedIndex = 0;
  bool _estTransporteur = false;
  String _prenom = '';

  @override
  void initState() {
    super.initState();
    _loadProfile();
    // Après connexion : ce téléphone reçoit les notifications push, et le
    // suivi GPS reprend si le transporteur a une course en cours de transport.
    final auth = ref.read(authServiceProvider);
    PushService.enregistrerAppareil(auth);
    GpsService.demarrerSiNecessaire(auth);
  }

  Future<void> _loadProfile() async {
    try {
      final profil = await ref.read(profileServiceProvider).getMonProfil();
      if (mounted) {
        setState(() {
          _estTransporteur = profil?['est_transporteur'] == true;
          _prenom = (profil?['prenom'] as String?) ?? '';
        });
      }
    } catch (_) {
      // Si le profil ne charge pas, on reste prudent et on masque l'onglet
      // Trajets (il redemandera le rôle transporteur au prochain chargement).
    }
  }

  // L'onglet "Trajets" ne concerne que les transporteurs : un client qui n'a
  // pas encore déclaré de véhicule n'a pas accès à /api/trajets/ côté
  // backend (403), donc on ne lui montre même pas l'onglet.
  List<Widget> get _screens => [
        _HomeTab(prenom: _prenom, estTransporteur: _estTransporteur, onProfilChange: _loadProfile),
        const ActivityScreen(),
        if (_estTransporteur) const TripsScreen(),
        const ProfileScreen(),
      ];

  List<BottomNavigationBarItem> get _navItems => [
        const BottomNavigationBarItem(
          icon: Icon(Icons.home_outlined),
          activeIcon: Icon(Icons.home),
          label: 'Accueil',
        ),
        const BottomNavigationBarItem(
          icon: Icon(Icons.history_outlined),
          activeIcon: Icon(Icons.history),
          label: 'Activité',
        ),
        if (_estTransporteur)
          const BottomNavigationBarItem(
            icon: Icon(Icons.local_shipping_outlined),
            activeIcon: Icon(Icons.local_shipping),
            label: 'Trajets',
          ),
        const BottomNavigationBarItem(
          icon: Icon(Icons.person_outline),
          activeIcon: Icon(Icons.person),
          label: 'Profil',
        ),
      ];

  @override
  Widget build(BuildContext context) {
    final screens = _screens;
    final navItems = _navItems;
    // Si le rôle transporteur vient de disparaître de la liste (ex. juste
    // après le premier chargement du profil) et que l'onglet sélectionné
    // n'existe plus, on retombe sur l'accueil plutôt que de planter.
    final safeIndex = _selectedIndex < screens.length ? _selectedIndex : 0;

    return Scaffold(
      body: IndexedStack(
        index: safeIndex,
        children: screens,
      ),
      bottomNavigationBar: BottomNavigationBar(
        currentIndex: safeIndex,
        onTap: (index) => setState(() => _selectedIndex = index),
        items: navItems,
        type: BottomNavigationBarType.fixed,
      ),
    );
  }
}

class _HomeTab extends ConsumerStatefulWidget {
  final String prenom;
  final bool estTransporteur;
  final Future<void> Function() onProfilChange;

  const _HomeTab({required this.prenom, required this.estTransporteur, required this.onProfilChange});

  @override
  ConsumerState<_HomeTab> createState() => _HomeTabState();
}

class _HomeTabState extends ConsumerState<_HomeTab> {
  List<Course> _recentCourses = [];
  int _nonLues = 0;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadRecent();
  }

  Future<void> _loadRecent() async {
    try {
      final courses = await ref.read(courseServiceProvider).getMyCourses();
      if (mounted) {
        setState(() {
          _recentCourses = courses.take(3).toList();
          _isLoading = false;
        });
      }
    } catch (_) {
      if (mounted) setState(() => _isLoading = false);
    }
    _loadNonLues();
  }

  Future<void> _loadNonLues() async {
    try {
      final nombre = await ref.read(notificationServiceProvider).getNombreNonLues();
      if (mounted) setState(() => _nonLues = nombre);
    } catch (_) {
      // Le badge est secondaire : on ignore une erreur réseau ponctuelle.
    }
  }

  Future<void> _rafraichir() async {
    await widget.onProfilChange();
    await _loadRecent();
  }

  Future<void> _ouvrir(String route) async {
    await context.push(route);
    if (mounted) _loadRecent();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(
        // Symbole du logo (sans le nom) à la place du titre.
        title: Image.asset('assets/images/logo_symbole.png', height: 36),
        centerTitle: true,
        actions: [
          IconButton(
            tooltip: l10n.notifications,
            icon: Badge(
              isLabelVisible: _nonLues > 0,
              label: Text(_nonLues > 99 ? '99+' : '$_nonLues'),
              child: const Icon(Icons.notifications_outlined),
            ),
            onPressed: () => _ouvrir('/notifications'),
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: _rafraichir,
        child: ListView(
          physics: const AlwaysScrollableScrollPhysics(),
          padding: const EdgeInsets.all(16),
          children: [
            // Salutation, nouvelle expédition et nouveau trajet : même largeur.
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 8),
              child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      widget.prenom.isEmpty ? l10n.helloShort : l10n.helloName(widget.prenom),
                      style: Theme.of(context).textTheme.headlineMedium?.copyWith(fontWeight: FontWeight.w700),
                    ),
                    const SizedBox(height: 8),
                    Text(
                      l10n.homeSubtitle,
                      style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                            color: Theme.of(context).textTheme.bodyLarge?.color?.withValues(alpha: 0.7),
                          ),
                    ),
                  ],
                ),
            ),
            const SizedBox(height: 12),
            _ActionCard(
              icon: Icons.add_box_outlined,
              title: l10n.newShipment,
              subtitle: l10n.newShipmentSubtitle,
              color: AppColors.primaryBrown,
              onTap: () => _ouvrir('/new-shipment'),
            ),
            if (widget.estTransporteur) ...[
              const SizedBox(height: 12),
              _ActionCard(
                icon: Icons.local_shipping_outlined,
                title: l10n.newTrip,
                subtitle: l10n.newTripSubtitle,
                color: AppColors.accentBrown,
                onTap: () => _ouvrir('/new-trip'),
              ),
            ],
            const SizedBox(height: 24),
            Text(l10n.recentActivity, style: Theme.of(context).textTheme.titleLarge),
            const SizedBox(height: 12),
            if (_isLoading)
              const Center(child: Padding(padding: EdgeInsets.all(24), child: CircularProgressIndicator()))
            else if (_recentCourses.isEmpty)
              Padding(
                padding: const EdgeInsets.symmetric(vertical: 24),
                child: Text(
                  l10n.noActivityYet,
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Theme.of(context).textTheme.bodyMedium?.color?.withValues(alpha: 0.6),
                      ),
                ),
              )
            else
              ..._recentCourses.map((course) => CarteVehicule(
                    typeVehicule: course.typeVehicule,
                    couleur: couleurStatutCourse(course.statut),
                    titre: '${course.demande['origine'] ?? ''} → ${course.demande['destination'] ?? ''}',
                    sousTitre: '${course.demande['poids_estime_kg'] ?? '?'} kg',
                    trailing: PastilleStatut(
                      texte: libelleStatutCourse(l10n, course.statut, role: course.role),
                      couleur: couleurStatutCourse(course.statut),
                    ),
                    onTap: () => _ouvrir('/shipment/${course.id}'),
                  )),
          ],
        ),
      ),
    );
  }
}

/// Bloc d'action pleine largeur (icône à gauche, texte à droite).
class _ActionCard extends StatelessWidget {
  final IconData icon;
  final String title;
  final String subtitle;
  final Color color;
  final VoidCallback onTap;

  const _ActionCard({
    required this.icon,
    required this.title,
    required this.subtitle,
    required this.color,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: EdgeInsets.zero,
      child: InkWell(
        onTap: onTap,
        borderRadius: BorderRadius.circular(16),
        child: Padding(
          padding: const EdgeInsets.all(20),
          child: Row(
            children: [
              Container(
                width: 56,
                height: 56,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.1),
                  borderRadius: BorderRadius.circular(16),
                ),
                child: Icon(icon, size: 28, color: color),
              ),
              const SizedBox(width: 16),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      title,
                      style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      subtitle,
                      style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                            color: Theme.of(context).textTheme.bodyMedium?.color?.withValues(alpha: 0.7),
                          ),
                    ),
                  ],
                ),
              ),
              Icon(Icons.chevron_right, color: color),
            ],
          ),
        ),
      ),
    );
  }
}
