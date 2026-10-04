import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../localization/app_localizations.dart';
import '../../services/shipment_service.dart';
import '../../theme/app_colors.dart';
import '../../utils/error_helper.dart';
import '../../utils/formatters.dart';
import '../../widgets/ai_rejection_dialog.dart';
import '../../widgets/common/custom_text_field.dart';
import '../../widgets/common/primary_button.dart';

/// Modification d'une demande (décision du 04/10/2026) :
/// - sans course : tout est modifiable ; nouvelle description ou nouvelle
///   vidéo → nouveau contrôle IA ;
/// - avec une course : date, prix (tant que le transporteur n'a pas
///   répondu) et numéro du destinataire uniquement.
class EditDemandeScreen extends ConsumerStatefulWidget {
  final String demandeId;

  const EditDemandeScreen({super.key, required this.demandeId});

  @override
  ConsumerState<EditDemandeScreen> createState() => _EditDemandeScreenState();
}

class _EditDemandeScreenState extends ConsumerState<EditDemandeScreen> {
  final _formKey = GlobalKey<FormState>();
  final _origine = TextEditingController();
  final _destination = TextEditingController();
  final _description = TextEditingController();
  final _poids = TextEditingController();
  final _montant = TextEditingController();
  final _telephone = TextEditingController();
  Shipment? _demande;
  DateTime? _date;
  File? _video;
  bool _isLoading = true;
  bool _isSaving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    for (final c in [_origine, _destination, _description, _poids, _montant, _telephone]) {
      c.dispose();
    }
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final d = await ref.read(shipmentServiceProvider).getShipment(widget.demandeId);
      _origine.text = d.origin;
      _destination.text = d.destination;
      _description.text = d.description;
      _poids.text = d.weightKg.toString();
      _montant.text = d.montantPropose.round().toString();
      _telephone.text = d.telephoneDestinataire;
      if (mounted) {
        setState(() {
          _demande = d;
          _date = d.preferredDate;
        });
      }
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

  bool get _avecCourse => _demande?.aUneCourse ?? false;

  /// Le prix reste modifiable tant que le transporteur n'a pas répondu.
  bool get _prixModifiable => !_avecCourse || _demande!.courseActive!['statut'] == 'reservee';

  Future<void> _choisirDate() async {
    final choisie = await showDatePicker(
      context: context,
      initialDate: _date ?? DateTime.now().add(const Duration(days: 1)),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
    );
    if (choisie != null) setState(() => _date = choisie);
  }

  Future<void> _filmer() async {
    final video = await ImagePicker().pickVideo(
      source: ImageSource.camera,
      maxDuration: const Duration(seconds: 60),
      preferredCameraDevice: CameraDevice.rear,
    );
    if (video != null) setState(() => _video = File(video.path));
  }

  Future<void> _enregistrer() async {
    if (!_formKey.currentState!.validate()) return;
    final d = _demande!;
    final champs = <String, dynamic>{};
    if (_date != null && formatDate(_date) != formatDate(d.preferredDate)) {
      champs['date_souhaitee'] = _date!.toIso8601String();
    }
    if (_telephone.text.trim() != d.telephoneDestinataire) {
      champs['telephone_destinataire'] = _telephone.text.trim();
    }
    final montant = double.parse(_montant.text);
    if (_prixModifiable && montant != d.montantPropose) champs['montant_propose'] = montant;
    if (!_avecCourse) {
      if (_origine.text.trim() != d.origin) champs['origine'] = _origine.text.trim();
      if (_destination.text.trim() != d.destination) champs['destination'] = _destination.text.trim();
      if (_description.text.trim() != d.description) champs['description'] = _description.text.trim();
      final poids = double.parse(_poids.text);
      if (poids != d.weightKg) champs['poids_estime_kg'] = poids;
    }
    if (champs.isEmpty && _video == null) {
      context.pop();
      return;
    }

    setState(() => _isSaving = true);
    try {
      final resultat = await ref.read(shipmentServiceProvider).updateShipment(d.id, champs, video: _video);
      if (!mounted) return;
      if (resultat.isRejected) {
        await afficherRejetIA(context, ref, demandeId: d.id, motif: resultat.motifRejet);
        if (mounted) context.pop();
      } else if (resultat.verdict == 'valide') {
        context.pushReplacement('/demande/${d.id}/succes');
      } else {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context).requestUpdated), backgroundColor: AppColors.success),
        );
        context.pop();
      }
    } catch (e) {
      _erreur(e);
    } finally {
      if (mounted) setState(() => _isSaving = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    String? requis(String? v) => (v == null || v.trim().isEmpty) ? l10n.fillAllFields : null;
    String? nombrePositif(String? v) {
      final n = double.tryParse(v ?? '');
      return (n == null || n <= 0) ? l10n.invalidNumber : null;
    }

    return Scaffold(
      appBar: AppBar(title: Text(l10n.editRequestTitle)),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : _demande == null
              ? Center(child: Text(l10n.error))
              : Form(
                  key: _formKey,
                  child: ListView(
                    padding: const EdgeInsets.all(16),
                    children: [
                      if (_avecCourse)
                        Card(
                          color: AppColors.info.withValues(alpha: 0.08),
                          child: Padding(
                            padding: const EdgeInsets.all(12),
                            child: Text(l10n.editLimitedWithCourse),
                          ),
                        ),
                      const SizedBox(height: 8),
                      CustomTextField(
                        controller: _origine,
                        label: l10n.origin,
                        prefixIcon: Icons.location_on_outlined,
                        enabled: !_avecCourse,
                        validator: requis,
                      ),
                      const SizedBox(height: 16),
                      CustomTextField(
                        controller: _destination,
                        label: l10n.destination,
                        prefixIcon: Icons.location_on_outlined,
                        enabled: !_avecCourse,
                        validator: requis,
                      ),
                      const SizedBox(height: 16),
                      InkWell(
                        onTap: _choisirDate,
                        child: InputDecorator(
                          decoration: InputDecoration(
                            labelText: l10n.date,
                            prefixIcon: const Icon(Icons.calendar_today_outlined),
                            border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                          ),
                          child: Text(formatDate(_date)),
                        ),
                      ),
                      const SizedBox(height: 16),
                      CustomTextField(
                        controller: _description,
                        label: l10n.description,
                        prefixIcon: Icons.description_outlined,
                        maxLines: 3,
                        enabled: !_avecCourse,
                        validator: requis,
                      ),
                      const SizedBox(height: 16),
                      CustomTextField(
                        controller: _poids,
                        label: l10n.weight,
                        keyboardType: const TextInputType.numberWithOptions(decimal: true),
                        prefixIcon: Icons.monitor_weight_outlined,
                        enabled: !_avecCourse,
                        validator: nombrePositif,
                      ),
                      const SizedBox(height: 16),
                      CustomTextField(
                        controller: _montant,
                        label: l10n.priceYouOffer,
                        keyboardType: TextInputType.number,
                        prefixIcon: Icons.payments_outlined,
                        enabled: _prixModifiable,
                        validator: nombrePositif,
                      ),
                      const SizedBox(height: 16),
                      CustomTextField(
                        controller: _telephone,
                        label: l10n.recipientPhoneOptional,
                        hint: '6XXXXXXXX',
                        keyboardType: TextInputType.phone,
                        prefixIcon: Icons.person_pin_circle_outlined,
                      ),
                      if (!_avecCourse) ...[
                        const SizedBox(height: 16),
                        OutlinedButton.icon(
                          onPressed: _filmer,
                          icon: Icon(_video == null ? Icons.videocam_outlined : Icons.check_circle, color: _video == null ? null : AppColors.success),
                          label: Text(_video == null ? l10n.refilmItem : l10n.newVideoReady),
                        ),
                        const SizedBox(height: 4),
                        Text(l10n.editTriggersAiCheck, style: Theme.of(context).textTheme.bodySmall),
                      ],
                      const SizedBox(height: 24),
                      PrimaryButton(text: l10n.save, onPressed: _isSaving ? null : _enregistrer, isLoading: _isSaving),
                    ],
                  ),
                ),
    );
  }
}
