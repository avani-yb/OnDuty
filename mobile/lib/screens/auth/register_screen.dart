import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../../localization/app_localizations.dart';
import '../../../theme/app_colors.dart';
import '../../../widgets/common/custom_text_field.dart';
import '../../../widgets/common/primary_button.dart';
import '../../../widgets/common/secondary_button.dart';
import '../../../services/auth_service.dart';
import '../../../utils/error_helper.dart';

class RegisterScreen extends ConsumerStatefulWidget {
  const RegisterScreen({super.key});

  @override
  ConsumerState<RegisterScreen> createState() => _RegisterScreenState();
}

class _RegisterScreenState extends ConsumerState<RegisterScreen> {
  final _formKey = GlobalKey<FormState>();
  final _phoneController = TextEditingController();
  final _passwordController = TextEditingController();
  final _confirmPasswordController = TextEditingController();
  final _nomController = TextEditingController();
  final _prenomController = TextEditingController();
  final _emailController = TextEditingController();
  bool _isLoading = false;
  bool _obscurePassword = true;
  bool _obscureConfirmPassword = true;

  @override
  void dispose() {
    _phoneController.dispose();
    _passwordController.dispose();
    _confirmPasswordController.dispose();
    _nomController.dispose();
    _prenomController.dispose();
    _emailController.dispose();
    super.dispose();
  }

  Future<void> _register() async {
    if (!_formKey.currentState!.validate()) return;

    setState(() => _isLoading = true);

    try {
      await ref.read(authServiceProvider).register(
        telephone: _phoneController.text.trim(),
        password: _passwordController.text,
        nom: _nomController.text.trim(),
        prenom: _prenomController.text.trim(),
        email: _emailController.text.trim().isEmpty ? null : _emailController.text.trim(),
      );
      if (mounted) context.go('/home');
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
              const SizedBox(height: 20),
              Image.asset(
                Theme.of(context).brightness == Brightness.dark
                    ? 'assets/images/logo_sombre.png'
                    : 'assets/images/logo_transparent.png',
                height: 100,
              ),
              const SizedBox(height: 24),
              Text(
                l10n.welcome,
                style: Theme.of(context).textTheme.displayMedium?.copyWith(
                      fontWeight: FontWeight.w700,
                    ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 8),
              Text(
                l10n.register,
                style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                      fontWeight: FontWeight.w600,
                    ),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 40),
              Form(
                key: _formKey,
                child: Column(
                  children: [
                    Row(
                      children: [
                        Expanded(
                          child: CustomTextField(
                            controller: _prenomController,
                            label: l10n.firstName,
                            hint: l10n.firstName,
                            prefixIcon: Icons.person_outline,
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return l10n.fillAllFields;
                              }
                              return null;
                            },
                          ),
                        ),
                        const SizedBox(width: 16),
                        Expanded(
                          child: CustomTextField(
                            controller: _nomController,
                            label: l10n.name,
                            hint: l10n.name,
                            prefixIcon: Icons.person_outline,
                            validator: (value) {
                              if (value == null || value.isEmpty) {
                                return l10n.fillAllFields;
                              }
                              return null;
                            },
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 16),
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
                    const SizedBox(height: 16),
                    CustomTextField(
                      controller: _emailController,
                      label: l10n.email,
                      hint: l10n.email,
                      keyboardType: TextInputType.emailAddress,
                      prefixIcon: Icons.email_outlined,
                      validator: (value) {
                        if (value != null && value.isNotEmpty && !value.contains('@')) {
                          return l10n.invalidEmail;
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 16),
                    CustomTextField(
                      controller: _passwordController,
                      label: l10n.password,
                      obscureText: _obscurePassword,
                      prefixIcon: Icons.lock_outline,
                      suffixIcon: IconButton(
                        icon: Icon(
                          _obscurePassword ? Icons.visibility_off : Icons.visibility,
                          color: Theme.of(context).iconTheme.color?.withOpacity(0.5),
                        ),
                        onPressed: () => setState(() => _obscurePassword = !_obscurePassword),
                      ),
                      validator: (value) {
                        if (value == null || value.isEmpty) {
                          return 'Veuillez entrer un mot de passe';
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
                        if (value != _passwordController.text) {
                          return l10n.passwordsDontMatch;
                        }
                        return null;
                      },
                    ),
                    const SizedBox(height: 24),
                    PrimaryButton(
                      text: l10n.register,
                      onPressed: _register,
                      isLoading: _isLoading,
                    ),
                    const SizedBox(height: 16),
                    SecondaryButton(
                      text: l10n.login,
                      onPressed: () => context.pop(),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 24),
              Row(
                mainAxisAlignment: MainAxisAlignment.center,
                children: [
                  Text(
                    'Déjà un compte ? ',
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