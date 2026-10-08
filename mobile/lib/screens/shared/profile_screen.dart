import 'dart:io';

import 'package:dio/dio.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:image_picker/image_picker.dart';

import '../../services/gps_service.dart';
import '../../services/push_service.dart';
import '../../../localization/app_localizations.dart';
import '../../../theme/app_colors.dart';
import '../../../utils/error_helper.dart';
import '../../../services/auth_service.dart';

final profileServiceProvider = Provider<ProfileService>((ref) {
  return ProfileService(ref.read(authServiceProvider));
});

/// Petit service dédié au profil : `/api/profil/<id>/` a besoin de l'id de
/// l'utilisateur connecté, extrait du JWT par `AuthService`.
class ProfileService {
  final AuthService _authService;
  ProfileService(this._authService);

  Future<Map<String, dynamic>?> getMonProfil() async {
    final userId = await _authService.getUserId();
    if (userId == null) return null;
    final response = await _authService.dio.get('/profil/$userId/');
    return response.data;
  }

  Future<Map<String, dynamic>?> updatePhoto(File photo) async {
    final userId = await _authService.getUserId();
    if (userId == null) return null;
    final formData = FormData.fromMap({
      'photo_profil': await MultipartFile.fromFile(photo.path),
    });
    final response = await _authService.dio.patch('/profil/$userId/', data: formData);
    return response.data;
  }

  /// Numéro qui reçoit les versements et remboursements (vide = téléphone du compte).
  Future<Map<String, dynamic>?> updateNumeroMobileMoney(String numero) async {
    final userId = await _authService.getUserId();
    if (userId == null) return null;
    final response = await _authService.dio.patch('/profil/$userId/', data: {'numero_mobile_money': numero});
    return response.data;
  }
}

class ProfileScreen extends ConsumerStatefulWidget {
  const ProfileScreen({super.key});

  @override
  ConsumerState<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends ConsumerState<ProfileScreen> {
  Map<String, dynamic>? _profil;
  bool _isLoading = true;
  bool _isUploadingPhoto = false;

  @override
  void initState() {
    super.initState();
    _loadProfil();
  }

  Future<void> _loadProfil() async {
    try {
      final profil = await ref.read(profileServiceProvider).getMonProfil();
      if (mounted) setState(() => _profil = profil);
    } catch (_) {
      // En cas d'échec, on affiche quand même l'écran avec des infos minimales.
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _changePhoto() async {
    final XFile? image = await ImagePicker().pickImage(
      source: ImageSource.gallery,
      maxWidth: 1024,
      imageQuality: 85,
    );
    if (image == null) return;

    setState(() => _isUploadingPhoto = true);
    try {
      final profil = await ref.read(profileServiceProvider).updatePhoto(File(image.path));
      if (mounted && profil != null) {
        setState(() => _profil = profil);
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(friendlyError(e)), backgroundColor: AppColors.error),
        );
      }
    } finally {
      if (mounted) setState(() => _isUploadingPhoto = false);
    }
  }

  Future<void> _modifierNumeroMobileMoney() async {
    final l10n = AppLocalizations.of(context);
    final controleur = TextEditingController(text: (_profil?['numero_mobile_money'] as String?) ?? '');
    final numero = await showDialog<String>(
      context: context,
      builder: (c) => AlertDialog(
        title: Text(l10n.mobileMoneyPayoutNumber),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Text(l10n.mobileMoneyPayoutHint, style: Theme.of(c).textTheme.bodySmall),
            TextField(
              controller: controleur,
              keyboardType: TextInputType.phone,
              decoration: const InputDecoration(hintText: '6XXXXXXXX'),
            ),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(c), child: Text(l10n.cancel)),
          FilledButton(onPressed: () => Navigator.pop(c, controleur.text.trim()), child: Text(l10n.save)),
        ],
      ),
    );
    if (numero == null) return;
    try {
      final profil = await ref.read(profileServiceProvider).updateNumeroMobileMoney(numero);
      if (mounted && profil != null) {
        setState(() => _profil = profil);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(l10n.mobileMoneyNumberSaved), backgroundColor: AppColors.success),
        );
      }
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(friendlyError(e)), backgroundColor: AppColors.error),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final nom = _profil?['nom'] ?? '';
    final prenom = _profil?['prenom'] ?? '';
    final telephone = _profil?['telephone'] ?? '';
    final email = _profil?['email'];
    final estTransporteur = _profil?['est_transporteur'] == true;
    final photoUrl = AuthService.absoluteMediaUrl(_profil?['photo_profil'] as String?);
    final scoreFiabilite = _profil?['score_fiabilite'];

    return Scaffold(
      appBar: AppBar(title: Text(l10n.profile)),
      body: _isLoading
          ? const Center(child: CircularProgressIndicator())
          : ListView(
              padding: const EdgeInsets.all(16),
              children: [
                Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Row(
                      children: [
                        Stack(
                          children: [
                            CircleAvatar(
                              radius: 40,
                              backgroundColor: AppColors.primaryBrown.withValues(alpha: 0.1),
                              backgroundImage: photoUrl != null ? NetworkImage(photoUrl) : null,
                              child: _isUploadingPhoto
                                  ? const CircularProgressIndicator()
                                  : photoUrl == null
                                      ? Icon(Icons.person, size: 40, color: AppColors.primaryBrown)
                                      : null,
                            ),
                            Positioned(
                              right: 0,
                              bottom: 0,
                              child: GestureDetector(
                                onTap: _isUploadingPhoto ? null : _changePhoto,
                                child: Container(
                                  padding: const EdgeInsets.all(4),
                                  decoration: BoxDecoration(
                                    color: AppColors.primaryBrown,
                                    shape: BoxShape.circle,
                                    border: Border.all(color: Theme.of(context).cardColor, width: 2),
                                  ),
                                  child: const Icon(Icons.camera_alt, size: 16, color: Colors.white),
                                ),
                              ),
                            ),
                          ],
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: Column(
                            crossAxisAlignment: CrossAxisAlignment.start,
                            children: [
                              Text(
                                '$prenom $nom'.trim().isEmpty ? telephone : '$prenom $nom',
                                style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w600),
                              ),
                              const SizedBox(height: 4),
                              Text(email != null && email.toString().isNotEmpty ? email : telephone, style: Theme.of(context).textTheme.bodyMedium),
                              const SizedBox(height: 8),
                              Row(
                                children: [
                                  Icon(Icons.star, size: 16, color: Colors.amber[700]),
                                  const SizedBox(width: 4),
                                  Text(
                                    scoreFiabilite != null ? '${scoreFiabilite.toStringAsFixed(1)} / 100' : '—',
                                    style: TextStyle(color: Colors.amber[800], fontWeight: FontWeight.w600),
                                  ),
                                ],
                              ),
                              if (estTransporteur) ...[
                                const SizedBox(height: 8),
                                Chip(
                                  label: Text(l10n.roleCarrier),
                                  backgroundColor: AppColors.accentBrown.withValues(alpha: 0.1),
                                  labelStyle: TextStyle(color: AppColors.accentBrown),
                                ),
                              ],
                            ],
                          ),
                        ),
                      ],
                    ),
                  ),
                ),
                const SizedBox(height: 16),
                _MenuItem(
                  icon: Icons.credit_card_outlined,
                  title: 'Mes expéditions',
                  onTap: () => context.push('/activity'),
                ),
                if (estTransporteur)
                  _MenuItem(
                    icon: Icons.local_shipping_outlined,
                    title: l10n.myTrips,
                    onTap: () => context.push('/trips'),
                  ),
                _MenuItem(
                  icon: Icons.receipt_long_outlined,
                  title: 'Historique des paiements',
                  onTap: () => context.push('/payment-history'),
                ),
                _MenuItem(
                  icon: Icons.account_balance_wallet_outlined,
                  title: l10n.mobileMoneyPayoutNumber,
                  subtitle: ((_profil?['numero_mobile_money'] as String?) ?? '').isNotEmpty
                      ? _profil!['numero_mobile_money'] as String
                      : l10n.mobileMoneyDefaultAccountPhone,
                  onTap: _modifierNumeroMobileMoney,
                ),
                _MenuItem(
                  icon: Icons.verified_user_outlined,
                  title: l10n.verifyCNI,
                  onTap: () => context.push('/verification'),
                ),
                if (!estTransporteur)
                  _MenuItem(
                    icon: Icons.directions_car_outlined,
                    title: l10n.becomeTransporter,
                    onTap: () => context.push('/become-transporter'),
                  ),
                const SizedBox(height: 16),
                _MenuItem(
                  icon: Icons.settings_outlined,
                  title: l10n.settings,
                  onTap: () => context.push('/settings'),
                ),
                _MenuItem(
                  icon: Icons.help_outline,
                  title: l10n.help,
                  onTap: () {},
                ),
                _MenuItem(
                  icon: Icons.info_outline,
                  title: l10n.about,
                  onTap: () {},
                ),
                const SizedBox(height: 16),
                _MenuItem(
                  icon: Icons.logout,
                  title: l10n.logout,
                  isDestructive: true,
                  onTap: () => _showLogoutDialog(),
                ),
              ],
            ),
    );
  }

  void _showLogoutDialog() {
    showDialog(
      context: context,
      builder: (dialogContext) => AlertDialog(
        title: Text(AppLocalizations.of(dialogContext).logoutConfirm),
        actions: [
          TextButton(onPressed: () => Navigator.pop(dialogContext), child: const Text('Annuler')),
          FilledButton(
            onPressed: () async {
              Navigator.pop(dialogContext);
              final auth = ref.read(authServiceProvider);
              // Ce téléphone ne reçoit plus les notifications du compte et
              // cesse de partager sa position.
              await PushService.oublierAppareil(auth);
              await GpsService.arreter();
              await auth.logout();
              if (mounted) context.go('/login');
            },
            child: const Text('Déconnexion'),
          ),
        ],
      ),
    );
  }
}

class _MenuItem extends StatelessWidget {
  final IconData icon;
  final String title;
  final String? subtitle;
  final bool isDestructive;
  final VoidCallback onTap;

  const _MenuItem({
    required this.icon,
    required this.title,
    this.subtitle,
    this.isDestructive = false,
    required this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Card(
      margin: const EdgeInsets.only(bottom: 8),
      child: ListTile(
        leading: Icon(icon, color: isDestructive ? AppColors.error : null),
        title: Text(title, style: TextStyle(color: isDestructive ? AppColors.error : null)),
        subtitle: subtitle == null ? null : Text(subtitle!),
        trailing: const Icon(Icons.chevron_right),
        onTap: onTap,
      ),
    );
  }
}
