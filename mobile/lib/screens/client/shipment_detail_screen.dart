import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../localization/app_localizations.dart';
import '../../services/course_service.dart';
import '../../services/gps_service.dart';
import '../../theme/app_colors.dart';
import '../../utils/error_helper.dart';
import '../../utils/formatters.dart';
import '../../widgets/common/vehicle_icon.dart';
import '../../widgets/suivi_map.dart';

/// Détail d'une course, adapté au rôle de l'utilisateur :
/// - expéditeur : accepter/refuser une proposition, payer, annuler,
///   confirmer la réception ;
/// - transporteur : accepter ou proposer un prix, faire avancer le
///   transport, signaler un incident ;
/// - destinataire inscrit : suivre et confirmer la réception.
class ShipmentDetailScreen extends ConsumerStatefulWidget {
  // Id de la Course (une demande matchée avec un trajet/transporteur).
  final String courseId;

  const ShipmentDetailScreen({super.key, required this.courseId});

  @override
  ConsumerState<ShipmentDetailScreen> createState() => _ShipmentDetailScreenState();
}

class _ShipmentDetailScreenState extends ConsumerState<ShipmentDetailScreen> {
  Course? _course;
  bool _isLoading = true;
  bool _isActing = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final course = await ref.read(courseServiceProvider).getCourse(widget.courseId);
      if (mounted) setState(() => _course = course);
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

  /// Exécute une action sur la course puis affiche le résultat.
  Future<void> _agir(Future<Course> Function(CourseService s) action, String succes) async {
    setState(() => _isActing = true);
    try {
      final course = await action(ref.read(courseServiceProvider));
      if (mounted) setState(() => _course = course);
      _message(succes);
    } catch (e) {
      _message(friendlyError(e), erreur: true);
    } finally {
      if (mounted) setState(() => _isActing = false);
    }
  }

  Future<bool> _confirmer(String titre, String texte, String bouton) async {
    final l10n = AppLocalizations.of(context);
    final ok = await showDialog<bool>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(titre),
        content: Text(texte),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c, false), child: Text(l10n.back)),
          FilledButton(onPressed: () => Navigator.pop(c, true), child: Text(bouton)),
        ],
      ),
    );
    return ok == true;
  }

  Future<void> _annuler() async {
    final l10n = AppLocalizations.of(context);
    final refus = _course!.statut == 'proposition_montant';
    if (!await _confirmer(
      refus ? l10n.refuseProposalTitle : l10n.cancelCourseTitle,
      refus ? l10n.refuseProposalBody : l10n.cancelCourseBody,
      refus ? l10n.refuse : l10n.confirmCancellation,
    )) {
      return;
    }
    await _agir((s) => s.annuler(widget.courseId), refus ? l10n.proposalRefused : l10n.courseCancelledMessage);
  }

  Future<void> _proposerMontant() async {
    final l10n = AppLocalizations.of(context);
    final controleur = TextEditingController(text: _course!.montantConvenu.round().toString());
    final montant = await showDialog<double>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(l10n.proposeOtherPrice),
        content: TextField(
          controller: controleur,
          keyboardType: TextInputType.number,
          decoration: InputDecoration(labelText: l10n.amountFcfa),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c), child: Text(l10n.cancel)),
          FilledButton(
            onPressed: () => Navigator.pop(c, double.tryParse(controleur.text)),
            child: Text(l10n.send),
          ),
        ],
      ),
    );
    if (montant == null || montant <= 0) return;
    await _agir((s) => s.proposerMontant(widget.courseId, montant), l10n.proposalSentMessage);
  }

  Future<void> _signalerIncident() async {
    final l10n = AppLocalizations.of(context);
    final controleur = TextEditingController();
    final description = await showDialog<String>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(l10n.reportIncident),
        content: TextField(
          controller: controleur,
          maxLines: 4,
          decoration: InputDecoration(hintText: l10n.incidentHint),
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c), child: Text(l10n.cancel)),
          FilledButton(onPressed: () => Navigator.pop(c, controleur.text.trim()), child: Text(l10n.send)),
        ],
      ),
    );
    if (description == null || description.isEmpty) return;
    setState(() => _isActing = true);
    try {
      await ref.read(courseServiceProvider).signalerIncident(widget.courseId, description);
      _message(l10n.incidentReported);
    } catch (e) {
      _message(friendlyError(e), erreur: true);
    } finally {
      if (mounted) setState(() => _isActing = false);
    }
  }

  Future<void> _payer() async {
    await context.push('/payment/${widget.courseId}');
    if (mounted) _load();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final course = _course;

    return Scaffold(
      appBar: AppBar(title: Text(l10n.courseDetailTitle)),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : course == null
              ? Center(child: Text(l10n.error))
              : RefreshIndicator(
                  onRefresh: _load,
                  child: ListView(
                    physics: const AlwaysScrollableScrollPhysics(),
                    padding: const EdgeInsets.all(16),
                    children: [
                      if (course.suiviDisponible && !course.estTransporteur)
                        SuiviMap(courseId: course.id, typeVehicule: course.typeVehicule),
                      if (course.suiviDisponible && course.estTransporteur) _bandeauPartage(l10n),
                      _carteResume(l10n, course),
                      if (course.detailsVisuels != null) _carteDetailsIA(l10n, course.detailsVisuels!),
                      _carteAutrePartie(l10n, course),
                      _cartePrix(l10n, course),
                      const SizedBox(height: 8),
                      ..._actions(l10n, course),
                    ],
                  ),
                ),
    );
  }

  /// Rappel au transporteur que sa position est partagée avec le client.
  Widget _bandeauPartage(AppLocalizations l10n) {
    return Card(
      color: AppColors.info.withValues(alpha: 0.08),
      margin: const EdgeInsets.only(bottom: 12),
      child: ListTile(
        leading: const Icon(Icons.my_location, color: AppColors.info),
        title: Text(l10n.locationSharedTitle),
        subtitle: Text(l10n.locationSharedBody),
      ),
    );
  }

  /// Départ : le partage de position doit être autorisé « Toujours » pour
  /// fonctionner téléphone en poche.
  Future<void> _marquerDepart() async {
    final l10n = AppLocalizations.of(context);
    final ok = await _confirmer(l10n.locationPermissionTitle, l10n.locationPermissionBody, l10n.allow);
    if (!ok) return;
    final autorise = await GpsService.permissionArrierePlan();
    if (!autorise && mounted) {
      _message(l10n.locationPermissionDenied, erreur: true);
      if (!await GpsService.permissionAccordee()) return;
    }
    await _agir((svc) => svc.avancerStatut(widget.courseId, 'depart'), l10n.statusUpdated);
    if (_course?.statut == 'depart') await GpsService.demarrer();
  }

  Widget _carteResume(AppLocalizations l10n, Course course) {
    final couleur = couleurStatutCourse(course.statut);
    final dateSouhaitee = DateTime.tryParse(course.demande['date_souhaitee'] ?? '');
    final telephone = (course.demande['telephone_destinataire'] as String?) ?? '';
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Expanded(
                  child: Text(
                    '${course.demande['origine'] ?? ''} → ${course.demande['destination'] ?? ''}',
                    style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w600),
                  ),
                ),
                Container(
                  padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
                  decoration: BoxDecoration(
                    color: couleur.withValues(alpha: 0.1),
                    borderRadius: BorderRadius.circular(20),
                  ),
                  child: Text(
                    libelleStatutCourse(l10n, course.statut, role: course.role),
                    style: TextStyle(color: couleur, fontWeight: FontWeight.w600),
                  ),
                ),
              ],
            ),
            if (course.statut == 'annulee' && course.motifAnnulation == 'suppression_trajet')
              Padding(
                padding: const EdgeInsets.only(top: 8),
                child: Text(l10n.cancelledByTripDeletion, style: const TextStyle(color: AppColors.error)),
              ),
            const SizedBox(height: 16),
            _Ligne(l10n.date, formatDate(dateSouhaitee)),
            _Ligne(l10n.weight, '${course.demande['poids_estime_kg']} kg'),
            _Ligne(l10n.description, course.demande['description'] ?? ''),
            if (telephone.isNotEmpty) _Ligne(l10n.recipientPhone, telephone),
            if (course.destinataire != null)
              _Ligne(l10n.roleRecipient, '${course.destinataire!['prenom']} ${course.destinataire!['nom']}'),
            if (course.statut != 'reservee' && course.statut != 'proposition_montant' && course.statut != 'annulee')
              Align(
                alignment: Alignment.centerLeft,
                child: TextButton.icon(
                  onPressed: () => context.push('/tracking/${course.id}'),
                  icon: const Icon(Icons.timeline),
                  label: Text(l10n.tracking),
                ),
              ),
          ],
        ),
      ),
    );
  }

  /// Détails extraits par le contrôle IA : repère pour reconnaître le colis
  /// à la prise en charge (doc 12, section 5).
  Widget _carteDetailsIA(AppLocalizations l10n, Map<String, dynamic> details) {
    final libelles = {
      'type': l10n.itemType,
      'marque': l10n.itemBrand,
      'couleur': l10n.itemColor,
      'etat': l10n.itemCondition,
      'contenant': l10n.itemContainer,
    };
    final lignes = libelles.entries
        .where((e) => (details[e.key] ?? '').toString().isNotEmpty)
        .map((e) => _Ligne(e.value, details[e.key].toString()))
        .toList();
    if (lignes.isEmpty) return const SizedBox.shrink();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(children: [
              const Icon(Icons.smart_toy_outlined, color: AppColors.primaryBrown),
              const SizedBox(width: 8),
              Text(l10n.aiVerifiedDetails, style: Theme.of(context).textTheme.titleMedium),
            ]),
            const SizedBox(height: 12),
            ...lignes,
          ],
        ),
      ),
    );
  }

  Widget _carteAutrePartie(AppLocalizations l10n, Course course) {
    final personne = course.estTransporteur ? course.client : course.transporteur;
    final score = (personne['score_fiabilite'] as num?)?.toDouble();
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Row(
          children: [
            course.estTransporteur
                ? CircleAvatar(
                    radius: 24,
                    backgroundColor: AppColors.primaryBrown.withValues(alpha: 0.1),
                    child: const Icon(Icons.person, color: AppColors.primaryBrown),
                  )
                : VehicleBadge(typeVehicule: course.typeVehicule, color: AppColors.primaryBrown),
            const SizedBox(width: 12),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(course.estTransporteur ? l10n.roleSender : l10n.roleCarrier,
                      style: Theme.of(context).textTheme.bodySmall),
                  Text(
                    '${personne['prenom'] ?? ''} ${personne['nom'] ?? ''}',
                    style: Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w600),
                  ),
                  Text(personne['telephone'] ?? ''),
                ],
              ),
            ),
            if (!course.estTransporteur && score != null)
              Row(children: [
                const Icon(Icons.star, size: 16, color: Colors.amber),
                const SizedBox(width: 4),
                Text('${score.toStringAsFixed(1)}/100',
                    style: TextStyle(color: Colors.amber[800], fontWeight: FontWeight.w600)),
              ]),
          ],
        ),
      ),
    );
  }

  Widget _cartePrix(AppLocalizations l10n, Course course) {
    String? explication;
    if (course.statut == 'reservee') {
      explication = course.estTransporteur ? l10n.priceInfoCarrierDecide : l10n.priceInfoWaitingCarrier;
    } else if (course.statut == 'proposition_montant') {
      final propose = course.demande['montant_propose'];
      explication = course.estTransporteur
          ? l10n.priceInfoWaitingClient
          : (course.initieePar == 'transporteur'
              ? l10n.priceInfoCarrierPickedYou(formatFcfa(propose as num?))
              : l10n.priceInfoCarrierCounter(formatFcfa(propose as num?)));
    } else if (course.statut == 'en_attente_paiement') {
      explication = course.estClient ? l10n.priceInfoPayNow : l10n.priceInfoWaitingPayment;
    }
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(l10n.agreedPrice, style: Theme.of(context).textTheme.titleMedium),
            const SizedBox(height: 8),
            Text(
              formatFcfa(course.montantConvenu),
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(
                    fontWeight: FontWeight.w700,
                    color: AppColors.primaryBrown,
                  ),
            ),
            if (explication != null) ...[
              const SizedBox(height: 8),
              Text(explication),
            ],
          ],
        ),
      ),
    );
  }

  List<Widget> _actions(AppLocalizations l10n, Course course) {
    final s = course.statut;
    final boutons = <Widget>[];
    void principal(IconData icone, String texte, VoidCallback action) =>
        boutons.add(_Bouton(icone: icone, texte: texte, onPressed: _isActing ? null : action));
    void secondaire(IconData icone, String texte, VoidCallback action, {bool danger = false}) => boutons.add(
        _Bouton(icone: icone, texte: texte, onPressed: _isActing ? null : action, secondaire: true, danger: danger));

    if (course.estClient) {
      if (s == 'proposition_montant') {
        principal(Icons.check, l10n.acceptProposal,
            () => _agir((svc) => svc.validerMontant(widget.courseId), l10n.proposalAccepted));
      }
      if (s == 'en_attente_paiement') principal(Icons.payment, l10n.payNow, _payer);
    }
    if (course.estTransporteur) {
      if (s == 'reservee') {
        principal(Icons.check, l10n.acceptReservation,
            () => _agir((svc) => svc.accepter(widget.courseId), l10n.reservationAccepted));
        secondaire(Icons.price_change_outlined, l10n.proposeOtherPrice, _proposerMontant);
      }
      const suivant = {'payee': 'depart', 'depart': 'en_route', 'en_route': 'arrivee'};
      if (suivant.containsKey(s)) {
        final action = suivant[s]!;
        final texte = {
          'depart': l10n.markDeparted,
          'en_route': l10n.markOnTheWay,
          'arrivee': l10n.markArrived,
        }[action]!;
        principal(
          Icons.flag_outlined,
          texte,
          action == 'depart'
              ? _marquerDepart
              : () => _agir((svc) => svc.avancerStatut(widget.courseId, action), l10n.statusUpdated),
        );
      }
      if (['payee', 'depart', 'en_route', 'arrivee'].contains(s)) {
        secondaire(Icons.report_problem_outlined, l10n.reportIncident, _signalerIncident);
      }
    }
    if (course.peutConfirmerReception) {
      principal(Icons.check_circle, l10n.confirmReception, () async {
        if (await _confirmer(l10n.confirmReception, l10n.confirmReceptionBody, l10n.confirm)) {
          await _agir((svc) => svc.confirmerReception(widget.courseId), l10n.receptionConfirmed);
        }
      });
    }
    if (course.estClient && !['livree', 'annulee', 'en_litige'].contains(s)) {
      secondaire(
        Icons.cancel_outlined,
        s == 'proposition_montant' ? l10n.refuseProposal : l10n.cancelCourse,
        _annuler,
        danger: true,
      );
    }
    return boutons;
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
          SizedBox(width: 120, child: Text(label, style: TextStyle(color: Theme.of(context).hintColor))),
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
