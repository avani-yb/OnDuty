import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../localization/app_localizations.dart';
import '../../../theme/app_colors.dart';
import '../../../services/course_service.dart';

class TrackingScreen extends ConsumerStatefulWidget {
  // Id de la Course (pas de la Demande).
  final String courseId;

  const TrackingScreen({super.key, required this.courseId});

  @override
  ConsumerState<TrackingScreen> createState() => _TrackingScreenState();
}

class _TrackingScreenState extends ConsumerState<TrackingScreen> {
  Course? _course;
  bool _isLoading = true;

  @override
  void initState() {
    super.initState();
    _loadCourse();
  }

  Future<void> _loadCourse() async {
    try {
      final course = await ref.read(courseServiceProvider).getCourse(widget.courseId);
      if (mounted) {
        setState(() {
          _course = course;
          _isLoading = false;
        });
      }
    } catch (e) {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final course = _course;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.tracking)),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : course == null
              ? Center(child: Text('Erreur de chargement'))
              : RefreshIndicator(
                  onRefresh: _loadCourse,
                  child: SingleChildScrollView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(20),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Row(
                                  mainAxisAlignment: MainAxisAlignment.spaceBetween,
                                  children: [
                                    Text('Statut', style: Theme.of(context).textTheme.labelLarge),
                                    Container(
                                      padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
                                      decoration: BoxDecoration(
                                        color: _getStatusColor(course.statut).withValues(alpha: 0.1),
                                        borderRadius: BorderRadius.circular(20),
                                      ),
                                      child: Text(
                                        _getStatusLabel(course.statut),
                                        style: TextStyle(
                                          color: _getStatusColor(course.statut),
                                          fontWeight: FontWeight.w600,
                                        ),
                                      ),
                                    ),
                                  ],
                                ),
                                const SizedBox(height: 20),
                                _TrackingStep(
                                  title: 'Réservé',
                                  description: 'Expédition créée, en attente de transporteur',
                                  isActive: ['reservee', 'en_attente_paiement', 'payee', 'depart', 'en_route', 'arrivee', 'livree'].contains(course.statut),
                                  isCompleted: !['reservee'].contains(course.statut),
                                ),
                                _TrackingStep(
                                  title: 'Paiement',
                                  description: 'Paiement en escrow',
                                  isActive: ['payee', 'depart', 'en_route', 'arrivee', 'livree'].contains(course.statut),
                                  isCompleted: !['reservee', 'en_attente_paiement'].contains(course.statut),
                                ),
                                _TrackingStep(
                                  title: 'Départ',
                                  description: 'Le transporteur a récupéré le colis',
                                  isActive: ['depart', 'en_route', 'arrivee', 'livree'].contains(course.statut),
                                  isCompleted: ['en_route', 'arrivee', 'livree'].contains(course.statut),
                                ),
                                _TrackingStep(
                                  title: 'En route',
                                  description: 'Colis en transit',
                                  isActive: ['en_route', 'arrivee', 'livree'].contains(course.statut),
                                  isCompleted: ['arrivee', 'livree'].contains(course.statut),
                                ),
                                _TrackingStep(
                                  title: 'Arrivée',
                                  description: 'Colis arrivé à destination',
                                  isActive: ['arrivee', 'livree'].contains(course.statut),
                                  isCompleted: course.statut == 'livree',
                                ),
                                _TrackingStep(
                                  title: 'Livré',
                                  description: 'Colis réceptionné par le client',
                                  isActive: course.statut == 'livree',
                                  isCompleted: course.statut == 'livree',
                                ),
                              ],
                            ),
                          ),
                        ),
                        const SizedBox(height: 24),
                        Card(
                          child: Padding(
                            padding: const EdgeInsets.all(16),
                            child: Column(
                              crossAxisAlignment: CrossAxisAlignment.start,
                              children: [
                                Text('Détails', style: Theme.of(context).textTheme.titleLarge),
                                const SizedBox(height: 12),
                                _DetailRow(label: 'Origine', value: course.demande['origine'] ?? ''),
                                _DetailRow(label: 'Destination', value: course.demande['destination'] ?? ''),
                                _DetailRow(label: 'Poids', value: '${course.demande['poids_estime_kg']} kg'),
                                _DetailRow(label: 'Transporteur', value: '${course.transporteur['prenom'] ?? ''} ${course.transporteur['nom'] ?? ''}'),
                                _DetailRow(label: 'Téléphone', value: course.transporteur['telephone'] ?? ''),
                              ],
                            ),
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
    );
  }

  Color _getStatusColor(String status) {
    switch (status) {
      case 'livree':
        return Colors.green;
      case 'en_litige':
        return Colors.red;
      case 'annulee':
        return Colors.grey;
      default:
        return AppColors.primaryBrown;
    }
  }

  String _getStatusLabel(String status) {
    switch (status) {
      case 'reservee':
        return 'En attente du transporteur';
      case 'proposition_montant':
        return 'Nouvelle somme proposée';
      case 'en_attente_paiement':
        return 'En attente de paiement';
      case 'payee':
        return 'Payée';
      case 'depart':
        return 'Départ';
      case 'en_route':
        return 'En route';
      case 'arrivee':
        return 'Arrivée';
      case 'livree':
        return 'Livrée';
      case 'annulee':
        return 'Annulée';
      case 'en_litige':
        return 'En litige';
      default:
        return status;
    }
  }
}

class _TrackingStep extends StatelessWidget {
  final String title;
  final String description;
  final bool isActive;
  final bool isCompleted;

  const _TrackingStep({
    required this.title,
    required this.description,
    required this.isActive,
    required this.isCompleted,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Column(
            children: [
              Container(
                width: 24,
                height: 24,
                decoration: BoxDecoration(
                  color: isCompleted
                      ? Colors.green
                      : isActive
                          ? AppColors.primaryBrown
                          : Theme.of(context).dividerColor,
                  shape: BoxShape.circle,
                  border: Border.all(
                    color: isCompleted
                        ? Colors.green
                        : isActive
                            ? AppColors.primaryBrown
                            : Theme.of(context).dividerColor,
                    width: 2,
                  ),
                ),
                child: isCompleted
                    ? const Icon(Icons.check, size: 14, color: Colors.white)
                    : isActive
                        ? Container(
                            width: 10,
                            height: 10,
                            decoration: BoxDecoration(
                              color: Colors.white,
                              shape: BoxShape.circle,
                            ),
                          )
                        : null,
              ),
              if (!isCompleted)
                Container(
                  width: 2,
                  height: 40,
                  color: Theme.of(context).dividerColor,
                  margin: const EdgeInsets.only(left: 11),
                ),
            ],
          ),
          const SizedBox(width: 16),
          Expanded(
            child: Padding(
              padding: const EdgeInsets.only(bottom: 24),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(
                          fontWeight: FontWeight.w600,
                          color: isActive
                              ? Theme.of(context).textTheme.titleMedium?.color
                              : Theme.of(context).textTheme.titleMedium?.color?.withValues(alpha: 0.5),
                        ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    description,
                    style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                          color: Theme.of(context).textTheme.bodyMedium?.color?.withValues(alpha: 0.7),
                        ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }
}

class _DetailRow extends StatelessWidget {
  final String label;
  final String value;

  const _DetailRow({required this.label, required this.value});

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 8),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          SizedBox(
            width: 100,
            child: Text(
              label,
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).textTheme.bodyMedium?.color?.withValues(alpha: 0.6),
                  ),
            ),
          ),
          Expanded(child: Text(value, style: Theme.of(context).textTheme.bodyMedium)),
        ],
      ),
    );
  }
}
