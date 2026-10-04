import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:image_picker/image_picker.dart';

import '../../../localization/app_localizations.dart';
import '../../../services/kyc_service.dart';
import '../../../theme/app_colors.dart';
import '../../../utils/error_helper.dart';
import '../../../widgets/common/primary_button.dart';
import '../../../widgets/common/secondary_button.dart';

/// Vérification de la CNI (KYC) : recto, verso puis selfie, envoyés au
/// backend. Si une vérification existe déjà, son statut est affiché.
class VerificationScreen extends ConsumerStatefulWidget {
  const VerificationScreen({super.key});

  @override
  ConsumerState<VerificationScreen> createState() => _VerificationScreenState();
}

class _VerificationScreenState extends ConsumerState<VerificationScreen> {
  final _photos = <File?>[null, null, null]; // recto, verso, selfie
  int _currentStep = 0;
  bool _isLoading = true;
  bool _isSubmitting = false;
  bool _recommencer = false;
  KycVerification? _verification;

  @override
  void initState() {
    super.initState();
    _charger();
  }

  Future<void> _charger() async {
    try {
      final verification = await ref.read(kycServiceProvider).getDerniereVerificationCni();
      if (mounted) setState(() => _verification = verification);
    } catch (e) {
      _afficherErreur(e);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _prendrePhoto() async {
    final selfie = _currentStep == 2;
    final XFile? image = await ImagePicker().pickImage(
      source: ImageSource.camera,
      preferredCameraDevice: selfie ? CameraDevice.front : CameraDevice.rear,
      maxWidth: 1600,
      imageQuality: 85,
    );
    if (image != null) setState(() => _photos[_currentStep] = File(image.path));
  }

  Future<void> _soumettre() async {
    setState(() => _isSubmitting = true);
    try {
      final verification = await ref.read(kycServiceProvider).soumettreCni(
            recto: _photos[0]!,
            verso: _photos[1]!,
            selfie: _photos[2]!,
          );
      if (mounted) {
        setState(() {
          _verification = verification;
          _recommencer = false;
        });
      }
    } catch (e) {
      _afficherErreur(e);
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  Future<void> _actualiser() async {
    setState(() => _isSubmitting = true);
    try {
      final verification = await ref.read(kycServiceProvider).actualiser(_verification!.id);
      if (mounted) setState(() => _verification = verification);
    } catch (e) {
      _afficherErreur(e);
    } finally {
      if (mounted) setState(() => _isSubmitting = false);
    }
  }

  void _afficherErreur(Object e) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(friendlyError(e)), backgroundColor: AppColors.error),
    );
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final verification = _verification;

    Widget body;
    if (_isLoading) {
      body = const Center(child: CircularProgressIndicator());
    } else if (verification != null && !(verification.estRejetee && _recommencer)) {
      body = _buildStatut(l10n, verification);
    } else {
      body = _buildCapture(l10n);
    }

    return Scaffold(
      appBar: AppBar(title: Text(l10n.verifyCNI)),
      body: SafeArea(child: body),
    );
  }

  Widget _buildStatut(AppLocalizations l10n, KycVerification verification) {
    final (IconData icone, Color couleur, String titre) = verification.estValidee
        ? (Icons.verified, AppColors.success, l10n.verificationSuccess)
        : verification.estRejetee
            ? (Icons.cancel, AppColors.error, l10n.verificationRejected)
            : (Icons.hourglass_top, AppColors.warning, l10n.verificationPending);

    return SingleChildScrollView(
      padding: const EdgeInsets.all(24),
      child: Column(
        children: [
          const SizedBox(height: 32),
          Icon(icone, size: 80, color: couleur),
          const SizedBox(height: 16),
          Text(titre, style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600)),
          const SizedBox(height: 12),
          Text(verification.motif, textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodyLarge),
          const SizedBox(height: 32),
          if (verification.estEnCours)
            PrimaryButton(
              text: l10n.refreshStatus,
              isLoading: _isSubmitting,
              onPressed: _isSubmitting ? null : _actualiser,
            ),
          if (verification.estRejetee)
            PrimaryButton(
              text: l10n.startNewVerification,
              onPressed: () => setState(() {
                _recommencer = true;
                _currentStep = 0;
                _photos.fillRange(0, 3, null);
              }),
            ),
        ],
      ),
    );
  }

  Widget _buildCapture(AppLocalizations l10n) {
    final titres = [l10n.cniFrontTitle, l10n.cniBackTitle, l10n.selfieTitle];
    final consignes = [l10n.cniFrontHint, l10n.cniBackHint, l10n.selfieHint];
    final photo = _photos[_currentStep];

    return Column(
      children: [
        Padding(
          padding: const EdgeInsets.all(16),
          child: Row(
            children: List.generate(3, (index) {
              return Expanded(
                child: Container(
                  height: 4,
                  margin: EdgeInsets.only(right: index < 2 ? 8 : 0),
                  decoration: BoxDecoration(
                    color: index <= _currentStep ? AppColors.primaryBrown : Theme.of(context).dividerColor,
                    borderRadius: BorderRadius.circular(2),
                  ),
                ),
              );
            }),
          ),
        ),
        Expanded(
          child: SingleChildScrollView(
            padding: const EdgeInsets.all(24),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  titres[_currentStep],
                  style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600),
                ),
                const SizedBox(height: 8),
                Text(
                  consignes[_currentStep],
                  style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                        color: Theme.of(context).textTheme.bodyMedium?.color?.withValues(alpha: 0.7),
                      ),
                ),
                const SizedBox(height: 24),
                InkWell(
                  onTap: _isSubmitting ? null : _prendrePhoto,
                  borderRadius: BorderRadius.circular(16),
                  child: Container(
                    width: double.infinity,
                    height: 250,
                    clipBehavior: Clip.antiAlias,
                    decoration: BoxDecoration(
                      border: Border.all(color: Theme.of(context).dividerColor, width: 2),
                      borderRadius: BorderRadius.circular(16),
                    ),
                    child: photo != null
                        ? Image.file(photo, fit: BoxFit.cover)
                        : Column(
                            mainAxisAlignment: MainAxisAlignment.center,
                            children: [
                              Icon(Icons.camera_alt, size: 64, color: Theme.of(context).iconTheme.color?.withValues(alpha: 0.3)),
                              const SizedBox(height: 16),
                              Text(l10n.tapToTakePhoto, style: Theme.of(context).textTheme.bodyLarge),
                            ],
                          ),
                  ),
                ),
                if (photo != null)
                  TextButton.icon(
                    onPressed: _isSubmitting ? null : _prendrePhoto,
                    icon: const Icon(Icons.refresh),
                    label: Text(l10n.retakePhoto),
                  ),
                const SizedBox(height: 16),
                if (_currentStep == 2)
                  Padding(
                    padding: const EdgeInsets.only(bottom: 16),
                    child: Text(l10n.kycConsent, style: Theme.of(context).textTheme.bodySmall),
                  ),
                if (_currentStep < 2)
                  PrimaryButton(
                    text: l10n.next,
                    onPressed: photo == null ? null : () => setState(() => _currentStep++),
                  )
                else
                  PrimaryButton(
                    text: l10n.submitForVerification,
                    isLoading: _isSubmitting,
                    onPressed: photo == null || _isSubmitting ? null : _soumettre,
                  ),
                if (_currentStep > 0) ...[
                  const SizedBox(height: 12),
                  SecondaryButton(
                    text: l10n.back,
                    onPressed: _isSubmitting ? null : () => setState(() => _currentStep--),
                  ),
                ],
              ],
            ),
          ),
        ),
      ],
    );
  }
}
