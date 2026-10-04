import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../localization/app_localizations.dart';
import '../../../theme/app_colors.dart';
import '../../../widgets/common/custom_text_field.dart';
import '../../../widgets/common/primary_button.dart';
import '../../../services/auth_service.dart';
import '../../../utils/error_helper.dart';

class ForgotPasswordScreen extends ConsumerStatefulWidget {
  const ForgotPasswordScreen({super.key});

  @override
  ConsumerState<ForgotPasswordScreen> createState() => _ForgotPasswordScreenState();
}

class _ForgotPasswordScreenState extends ConsumerState<ForgotPasswordScreen> {
  final _formKey = GlobalKey<FormState>();
  final _phoneController = TextEditingController();
  bool _isLoading = false;
  bool _codeSent = false;
  final _codeController = TextEditingController();
  final _newPasswordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  bool _obscureNewPassword = true;
  bool _obscureConfirmPassword = true;

  @override
  void dispose() {
    _phoneController.dispose();
    _codeController.dispose();
    _newPasswordController.dispose();
    _confirmPasswordController.dispose();
    super.dispose();
  }

  Future<void> _sendCode() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      await ref.read(authServiceProvider).requestPasswordReset(
        phone: _phoneController.text.trim(),
      );
      if (mounted) {
        setState(() => _codeSent = true);
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(AppLocalizations.of(context).verificationCodeSent),
            backgroundColor: AppColors.success,
          ),
        );
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

  Future<void> _verifyCodeAndReset() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      await ref.read(authServiceProvider).resetPassword(
        phone: _phoneController.text.trim(),
        code: _codeController.text.trim(),
        newPassword: _newPasswordController.text,
      );
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(
            content: Text(AppLocalizations.of(context).passwordChanged),
            backgroundColor: AppColors.success,
          ),
        );
        context.go('/login');
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

    return Scaffold(
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              const SizedBox(height: 40),
              Icon(
                Icons.lock_reset,
                size: 80,
                color: AppColors.primaryBrown,
              ),
              const SizedBox(height: 24),
              Text(
                l10n.forgotPassword,
                style: Theme.of(context).textTheme.displayMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                _codeSent
                    ? 'Entrez le code reçu et votre nouveau mot de passe'
                    : 'Entrez votre téléphone pour recevoir un code de réinitialisation',
                style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                      color: Theme.of(context).textTheme.bodyLarge?.color?.withOpacity(0.7),
                    ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 40),
              Form(
                key: _formKey,
                child: Column(
                  children: [
                    if (!_codeSent) ...[
                      CustomTextField(
                        controller: _phoneController,
                        label: l10n.phone,
                        hint: '+237 6XX XXX XXX',
                        keyboardType: TextInputType.phone,
                        prefixIcon: Icons.phone_outlined,
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Veuillez entrer votre téléphone';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 24),
                      PrimaryButton(
                        text: l10n.resendCode,
                        onPressed: _sendCode,
                        isLoading: _isLoading,
                      ),
                    ] else ...[
                      CustomTextField(
                        controller: _codeController,
                        label: 'Code de vérification',
                        hint: '6 chiffres',
                        keyboardType: TextInputType.number,
                        prefixIcon: Icons.vpn_key_outlined,
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Veuillez entrer le code';
                          }
                          if (value.length != 6) {
                            return 'Le code doit contenir 6 chiffres';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),
                      CustomTextField(
                        controller: _newPasswordController,
                        label: l10n.newPassword,
                        obscureText: _obscureNewPassword,
                        prefixIcon: Icons.lock_outline,
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscureNewPassword ? Icons.visibility_off : Icons.visibility,
                            color: Theme.of(context).iconTheme.color?.withOpacity(0.5),
                          ),
                          onPressed: () => setState(() => _obscureNewPassword = !_obscureNewPassword),
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Veuillez entrer un nouveau mot de passe';
                          }
                          if (value.length < 8) {
                            return 'Le mot de passe doit contenir au moins 8 caractères';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 16),
                      CustomTextField(
                        controller: _confirmPasswordController,
                        label: l10n.confirmPassword,
                        obscureText: _obscureConfirmPassword,
                        prefixIcon: Icons.lock_outline,
                        suffixIcon: IconButton(
                          icon: Icon(
                            _obscureConfirmPassword ? Icons.visibility_off : Icons.visibility,
                            color: Theme.of(context).iconTheme.color?.withOpacity(0.5),
                          ),
                          onPressed: () => setState(() => _obscureConfirmPassword = !_obscureConfirmPassword),
                        ),
                        validator: (value) {
                          if (value == null || value.isEmpty) {
                            return 'Veuillez confirmer votre mot de passe';
                          }
                          if (value != _newPasswordController.text) {
                            return 'Les mots de passe ne correspondent pas';
                          }
                          return null;
                        },
                      ),
                      const SizedBox(height: 24),
                      PrimaryButton(
                        text: l10n.confirm,
                        onPressed: _verifyCodeAndReset,
                        isLoading: _isLoading,
                      ),
                      const SizedBox(height: 16),
                      TextButton(
                        onPressed: () => setState(() => _codeSent = false),
                        child: Text('Renvoyer le code', style: TextStyle(color: AppColors.primaryBrown)),
                      ),
                    ],
                  ],
                ),
              ),
              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    'Retour à la ',
                    style: TextStyle(color: Theme.of(context).textTheme.bodyMedium?.color?.withOpacity(0.7)),
                  ),
                  TextButton(
                    onPressed: () => context.pop(),
                    child: Text(l10n.login, style: TextStyle(color: AppColors.primaryBrown)),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }
}