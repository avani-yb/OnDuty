import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../localization/app_localizations.dart';
import '../../../theme/app_colors.dart';
import '../../../widgets/common/custom_text_field.dart';
import '../../../widgets/common/primary_button.dart';
import '../../../widgets/common/secondary_button.dart';
import '../../../services/vehicule_service.dart';
import '../../../utils/error_helper.dart';
import '../../../utils/navigation_helper.dart';

/// Écran "Devenir transporteur" (BF-22) : déclarer les informations de son
/// véhicule. C'est cette action, côté serveur, qui active le rôle
/// Transporteur sur le compte (cf. vehicule/views.py::perform_create).
class BecomeTransporterScreen extends ConsumerStatefulWidget {
  const BecomeTransporterScreen({super.key});

  @override
  ConsumerState<BecomeTransporterScreen> createState() => _BecomeTransporterScreenState();
}

class _BecomeTransporterScreenState extends ConsumerState<BecomeTransporterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _marqueController = TextEditingController();
  final _modeleController = TextEditingController();
  final _immatriculationController = TextEditingController();
  final _capaciteController = TextEditingController();
  String _typeVehicule = 'camion';
  bool _isLoading = false;
  bool _isChecking = true;

  @override
  void initState() {
    super.initState();
    _checkExistingVehicle();
  }

  @override
  void dispose() {
    _marqueController.dispose();
    _modeleController.dispose();
    _immatriculationController.dispose();
    _capaciteController.dispose();
    super.dispose();
  }

  Future<void> _checkExistingVehicle() async {
    try {
      final vehicule = await ref.read(vehiculeServiceProvider).getMonVehicule();
      if (mounted && vehicule != null) {
        // Le rôle Transporteur est déjà actif : rien à faire ici.
        context.pushReplacement('/trips');
        return;
      }
    } catch (_) {
      // Pas de véhicule trouvé ou erreur réseau : on laisse le formulaire s'afficher.
    }
    if (mounted) setState(() => _isChecking = false);
  }

  Future<void> _submit() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);
    try {
      await ref.read(vehiculeServiceProvider).declarerVehicule(
            typeVehicule: _typeVehicule,
            marque: _marqueController.text.trim(),
            modele: _modeleController.text.trim(),
            immatriculation: _immatriculationController.text.trim(),
            capaciteMaxKg: double.parse(_capaciteController.text),
          );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context).vehicleAdded), backgroundColor: AppColors.success),
        );
        context.pushReplacement('/new-trip');
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(friendlyError(e)), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    if (_isChecking) {
      return Scaffold(
        appBar: AppBar(title: Text(l10n.becomeTransporter)),
        body: const Center(child: CircularProgressIndicator()),
      );
    }

    return Scaffold(
      appBar: AppBar(title: Text(l10n.becomeTransporter)),
      body: Form(
        key: _formKey,
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            Text(
              'Informations du véhicule',
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600),
            ),
            const SizedBox(height: 8),
            Text(
              'Ces informations sont nécessaires pour activer votre rôle transporteur.',
              style: Theme.of(context).textTheme.bodyMedium?.copyWith(
                    color: Theme.of(context).textTheme.bodyMedium?.color?.withValues(alpha: 0.7),
                  ),
            ),
            const SizedBox(height: 16),
            DropdownButtonFormField<String>(
              initialValue: _typeVehicule,
              decoration: InputDecoration(
                labelText: l10n.vehicleType,
                prefixIcon: const Icon(Icons.local_shipping_outlined),
                border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
              ),
              items: const [
                DropdownMenuItem(value: 'camion', child: Text('Camion')),
                DropdownMenuItem(value: 'pick-up', child: Text('Pick-up')),
                DropdownMenuItem(value: 'voiture', child: Text('Voiture')),
              ],
              onChanged: (v) => setState(() => _typeVehicule = v ?? 'camion'),
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _marqueController,
              label: l10n.brand,
              hint: 'Ex: Toyota',
              prefixIcon: Icons.directions_car_outlined,
              validator: (v) => v?.isEmpty ?? true ? l10n.fillAllFields : null,
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _modeleController,
              label: l10n.model,
              hint: 'Ex: Hilux',
              prefixIcon: Icons.directions_car_outlined,
              validator: (v) => v?.isEmpty ?? true ? l10n.fillAllFields : null,
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _immatriculationController,
              label: l10n.licensePlate,
              hint: 'Ex: LT-123-CM',
              prefixIcon: Icons.pin_outlined,
              validator: (v) => v?.isEmpty ?? true ? l10n.fillAllFields : null,
            ),
            const SizedBox(height: 16),
            CustomTextField(
              controller: _capaciteController,
              label: l10n.capacity,
              hint: 'Ex: 1000',
              keyboardType: TextInputType.numberWithOptions(decimal: true),
              prefixIcon: Icons.monitor_weight_outlined,
              validator: (v) {
                if (v?.isEmpty ?? true) return l10n.fillAllFields;
                if (double.tryParse(v!) == null) return 'Capacité invalide';
                if (double.parse(v) <= 0) return 'Capacité doit être > 0';
                return null;
              },
            ),
            const SizedBox(height: 24),
            PrimaryButton(
              text: l10n.becomeTransporter,
              onPressed: _submit,
              isLoading: _isLoading,
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
