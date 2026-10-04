import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../../localization/app_localizations.dart';
import '../../../theme/app_colors.dart';
import '../../theme/theme_provider.dart';

class SettingsScreen extends ConsumerStatefulWidget {
  const SettingsScreen({super.key});

  @override
  ConsumerState<SettingsScreen> createState() => _SettingsScreenState();
}

class _SettingsScreenState extends ConsumerState<SettingsScreen> {
  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final themeMode = ref.watch(themeProvider);

    return Scaffold(
      appBar: AppBar(title: Text(l10n.settings)),
      body: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(l10n.theme, style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 16),
                  _ThemeOption(
                    title: l10n.lightTheme,
                    subtitle: 'Toujours clair',
                    value: ThemeMode.light,
                    current: themeMode,
                    onChanged: (value) => ref.read(themeProvider.notifier).setTheme(value),
                  ),
                  _ThemeOption(
                    title: l10n.darkTheme,
                    subtitle: 'Toujours sombre',
                    value: ThemeMode.dark,
                    current: themeMode,
                    onChanged: (value) => ref.read(themeProvider.notifier).setTheme(value),
                  ),
                  _ThemeOption(
                    title: l10n.systemTheme,
                    subtitle: 'Suivre le système',
                    value: ThemeMode.system,
                    current: themeMode,
                    onChanged: (value) => ref.read(themeProvider.notifier).setTheme(value),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(l10n.language, style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 16),
                  ListTile(
                    leading: const Icon(Icons.language),
                    title: const Text('Français'),
                    trailing: Radio<Locale>(
                      value: const Locale('fr'),
                      groupValue: Localizations.localeOf(context),
                      onChanged: (value) {},
                    ),
                  ),
                  ListTile(
                    leading: const Icon(Icons.language),
                    title: const Text('English'),
                    trailing: Radio<Locale>(
                      value: const Locale('en'),
                      groupValue: Localizations.localeOf(context),
                      onChanged: (value) {},
                    ),
                  ),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Application', style: Theme.of(context).textTheme.titleLarge),
                  const SizedBox(height: 16),
                  ListTile(
                    leading: const Icon(Icons.info_outline),
                    title: Text(l10n.about),
                    onTap: () {},
                  ),
                  ListTile(
                    leading: const Icon(Icons.description_outlined),
                    title: Text(l10n.terms),
                    onTap: () {},
                  ),
                  ListTile(
                    leading: const Icon(Icons.privacy_tip_outlined),
                    title: Text(l10n.privacy),
                    onTap: () {},
                  ),
                  ListTile(
                    leading: const Icon(Icons.star_outline),
                    title: Text('Noter l\'application'),
                    onTap: () {},
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

class _ThemeOption extends StatelessWidget {
  final String title;
  final String subtitle;
  final ThemeMode value;
  final ThemeMode current;
  final void Function(ThemeMode) onChanged;

  const _ThemeOption({
    required this.title,
    required this.subtitle,
    required this.value,
    required this.current,
    required this.onChanged,
  });

  @override
  Widget build(BuildContext context) {
    return RadioListTile<ThemeMode>(
      title: Text(title, style: const TextStyle(fontWeight: FontWeight.w500)),
      subtitle: Text(subtitle),
      value: value,
      groupValue: current,
      onChanged: (value) => onChanged(value!),
      activeColor: AppColors.primaryBrown,
    );
  }
}