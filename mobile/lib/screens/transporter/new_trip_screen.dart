import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:dio/dio.dart';

import '../../../localization/app_localizations.dart';
import '../../../theme/app_colors.dart';
import '../../../widgets/common/custom_text_field.dart';
import '../../../widgets/common/primary_button.dart';
import '../../../widgets/common/secondary_button.dart';
import '../../../services/trip_service.dart';
import '../../../utils/error_helper.dart';
import '../../../utils/navigation_helper.dart';

class NewTripScreen extends ConsumerStatefulWidget {
  const NewTripScreen({super.key});

  @override
  ConsumerState<NewTripScreen> createState() => _NewTripScreenState();
}

class _NewTripScreenState extends ConsumerState<NewTripScreen> {
  final _formKey = GlobalKey<FormState>();
  final _originController = TextEditingController();
  final _destinationController = TextEditingController();
  final _capacityController = TextEditingController();
  DateTime? _selectedDate;
  bool _isLoading = false;

  @override
  void dispose() {
    _originController.dispose();
    _destinationController.dispose();
    _capacityController.dispose();
    super.dispose();
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
    if (_selectedDate == null) {
      ScaffoldMessenger.of(context).showSnackBar(
        SnackBar(content: Text(AppLocalizations.of(context).fillAllFields), backgroundColor: AppColors.error),
      );
      return;
    }

    setState(() => _isLoading = true);

    try {
      await ref.read(tripServiceProvider).createTrip(
        origin: _originController.text.trim(),
        destination: _destinationController.text.trim(),
        departureDate: _selectedDate!,
        capacityKg: double.parse(_capacityController.text),
      );

      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(AppLocalizations.of(context).tripPublished), backgroundColor: AppColors.success),
        );
        context.go('/trips');
      }
    } catch (e) {
      if (mounted) {
        // Le rôle Transporteur n'est pas encore actif (aucun véhicule déclaré) :
        // on guide l'utilisateur vers l'étape manquante plutôt que d'afficher
        // une erreur technique 403 incompréhensible.
        if (e is DioException && e.response?.statusCode == 403) {
          ScaffoldMessenger.of(context).showSnackBar(
            SnackBar(
              content: const Text('Vous devez d\'abord déclarer un véhicule pour publier un trajet.'),
              backgroundColor: AppColors.error,
            ),
          );
          context.go('/become-transporter');
          return;
        }
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

    return Scaffold(
      appBar: AppBar(title: Text(l10n.newTrip)),
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
            const SizedBox(height: 16),
            CustomTextField(
              controller: _capacityController,
              label: l10n.capacity,
              hint: 'Ex: 500',
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
              text: l10n.tripPublished,
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