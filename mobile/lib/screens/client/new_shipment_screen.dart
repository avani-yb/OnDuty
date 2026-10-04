import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../../localization/app_localizations.dart';
import '../../../theme/app_colors.dart';
import '../../../widgets/common/custom_text_field.dart';
import '../../../widgets/common/primary_button.dart';
import '../../../widgets/common/secondary_button.dart';
import '../../../services/shipment_service.dart';
import '../../../utils/error_helper.dart';
import '../../../utils/navigation_helper.dart';
import '../../../widgets/ai_rejection_dialog.dart';

class NewShipmentScreen extends ConsumerStatefulWidget {
  const NewShipmentScreen({super.key});

  @override
  ConsumerState<NewShipmentScreen> createState() => _NewShipmentScreenState();
}

class _NewShipmentScreenState extends ConsumerState<NewShipmentScreen> {
  final _formKey = GlobalKey<FormState>();
  final _originController = TextEditingController();
  final _destinationController = TextEditingController();
  final _descriptionController = TextEditingController();
  final _weightController = TextEditingController();
  final _montantController = TextEditingController();
  final _telephoneController = TextEditingController();
  DateTime? _selectedDate;
  File? _videoFile;
  bool _isSubmitting = false;

  @override
  void dispose() {
    _originController.dispose();
    _destinationController.dispose();
    _descriptionController.dispose();
    _weightController.dispose();
    _montantController.dispose();
    _telephoneController.dispose();
    super.dispose();
  }

  Future<void> _pickVideo() async {
    final XFile? video = await ImagePicker().pickVideo(
      source: ImageSource.camera,
      maxDuration: const Duration(seconds: 60),
      preferredCameraDevice: CameraDevice.rear,
    );

    if (video != null) {
      setState(() {
        _videoFile = File(video.path);
      });
    }
  }

  Future<void> _selectDate() async {
    final DateTime? picked = await showDatePicker(
      context: context,
      initialDate: DateTime.now().add(const Duration(days: 1)),
      firstDate: DateTime.now(),
      lastDate: DateTime.now().add(const Duration(days: 365)),
      locale: const Locale('fr'),
    );

    if (picked != null) {
      setState(() => _selectedDate = picked);
    }
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;
    if (_videoFile == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppLocalizations.of(context).chooseVideo), backgroundColor: AppColors.error),
      );
      return;
    }

    setState(() => _isSubmitting = true);

    try {
      final result = await ref.read(shipmentServiceProvider).createShipment(
        origin: _originController.text.trim(),
        destination: _destinationController.text.trim(),
        description: _descriptionController.text.trim(),
        weightKg: double.parse(_weightController.text),
        montantPropose: double.parse(_montantController.text),
        preferredDate: _selectedDate!,
        videoFile: _videoFile!,
        telephoneDestinataire: _telephoneController.text.trim(),
      );

      if (!mounted) return;
      if (result.isRejected) {
        // Le client peut corriger le formulaire, ou contester le rejet.
        final conteste = await afficherRejetIA(
          context,
          ref,
          demandeId: result.shipment.id,
          motif: result.motifRejet,
        );
        if (conteste && mounted) context.pushReplacement('/demande/${result.shipment.id}');
      } else {
        context.pushReplacement('/demande/${result.shipment.id}/succes');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(friendlyError(e)), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  Widget _buildVideoPreview() {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              children: [
                Icon(Icons.videocam, color: AppColors.primaryBrown),
                const SizedBox(width: 12),
                Expanded(
                  child: Text(
                    'Vidéo sélectionnée',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                ),
              ],
            ),
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: OutlinedButton.icon(
                    onPressed: _pickVideo,
                    icon: const Icon(Icons.refresh),
                    label: const Text('Reprendre'),
                  ),
                ),
                const SizedBox(width: 12),
                Expanded(
                  child: FilledButton.icon(
                    onPressed: () => setState(() => _videoFile = null),
                    icon: const Icon(Icons.delete),
                    label: const Text('Supprimer'),
                  ),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildVideoPlaceholder() {
    return Card(
      child: InkWell(
        onTap: _pickVideo,
        borderRadius: BorderRadius.circular(16),
        child: Container(
          height: 200,
          decoration: BoxDecoration(
            borderRadius: BorderRadius.circular(16),
            border: Border.all(
              color: Theme.of(context).dividerColor,
              style: BorderStyle.solid,
              width: 2,
            ),
          ),
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            children: [
              Container(
                width: 80,
                height: 80,
                decoration: BoxDecoration(
                  color: AppColors.primaryBrown.withValues(alpha: 0.1),
                  shape: BoxShape.circle,
                ),
                child: Icon(Icons.videocam, size: 40, color: AppColors.primaryBrown),
              ),
              const SizedBox(height: 16),
              Text(
                'Filmer l\'objet',
                style: Theme.of(context).textTheme.titleLarge?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
              ),
              const SizedBox(height: 8),
              Text(
                'Une vidéo courte (max 60s) est obligatoire pour le contrôle IA',
                style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                      color: Theme.of(context).textTheme.bodyMedium?.color?.withValues(alpha: 0.7),
                    ),
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.newShipment)),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              'Informations du trajet',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _originController,
              label: l10n.origin,
              hint: 'Ex: Douala',
              prefixIcon: Icons.location_on_outlined,
              validator: (v) => v?.isEmpty ?? true ? l10n.fillAllFields : null,
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _destinationController,
              label: l10n.destination,
              hint: 'Ex: Yaoundé',
              prefixIcon: Icons.location_on_outlined,
              validator: (v) => v?.isEmpty ?? true ? l10n.fillAllFields : null,
            ),
            const SizedBox(height: 16),
            InkWell(
              onTap: _selectDate,
              child: InputDecorator(
                decoration: InputDecoration(
                  labelText: l10n.date,
                  prefixIcon: const Icon(Icons.calendar_today_outlined),
                  border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
                ),
                child: Text(
                  _selectedDate == null
                      ? l10n.date
                      : '${_selectedDate!.day}/${_selectedDate!.month}/${_selectedDate!.year}',
                ),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'Détails de l\'expédition',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _descriptionController,
              label: l10n.description,
              hint: 'Décrivez l\'objet à expédier',
              prefixIcon: Icons.description_outlined,
              maxLines: 3,
              validator: (v) => v?.isEmpty ?? true ? l10n.fillAllFields : null,
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _weightController,
              label: l10n.weight,
              hint: 'Ex: 25.5',
              keyboardType: TextInputType.numberWithOptions(decimal: true),
              prefixIcon: Icons.monitor_weight_outlined,
              validator: (v) {
                if (v?.isEmpty ?? true) return l10n.fillAllFields;
                if (double.tryParse(v!) == null) return 'Poids invalide';
                if (double.parse(v) <= 0) return 'Poids doit être > 0';
                return null;
              },
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _montantController,
              label: 'Somme que vous êtes prêt à payer (FCFA)',
              hint: 'Ex: 10000',
              keyboardType: TextInputType.numberWithOptions(decimal: true),
              prefixIcon: Icons.payments_outlined,
              validator: (v) {
                if (v?.isEmpty ?? true) return l10n.fillAllFields;
                if (double.tryParse(v!) == null) return 'Montant invalide';
                if (double.parse(v) <= 0) return 'Montant doit être > 0';
                return null;
              },
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _telephoneController,
              label: l10n.recipientPhoneOptional,
              hint: '6XXXXXXXX',
              keyboardType: TextInputType.phone,
              prefixIcon: Icons.person_pin_circle_outlined,
              validator: (v) {
                final chiffres = (v ?? '').replaceAll(RegExp(r'\D'), '');
                if (chiffres.isNotEmpty && (chiffres.length < 8 || chiffres.length > 15)) {
                  return l10n.invalidPhone;
                }
                return null;
              },
            ),
            const SizedBox(height: 4),
            Text(l10n.recipientPhoneHint, style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 24),
            Text(
              'Vidéo de l\'objet (obligatoire)',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 12),
            _videoFile != null ? _buildVideoPreview() : _buildVideoPlaceholder(),
            const SizedBox(height: 24),
            PrimaryButton(
              text: l10n.submit,
              onPressed: _submit,
              isLoading: _isSubmitting,
            ),
            const SizedBox(height: 16),
            SecondaryButton(
              text: l10n.cancel,
              onPressed: () => safePop(context),
            ),
          ],
        ),
      ),
    );
  }
}