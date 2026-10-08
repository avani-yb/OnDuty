import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'theme/app_theme.dart';
import 'theme/theme_provider.dart';
import 'localization/app_localizations.dart';
import 'routing/app_router.dart';
import 'services/gps_service.dart';
import 'services/push_service.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  // Notifications (push si Firebase est configuré) et suivi GPS : un échec
  // ne doit jamais empêcher l'application de démarrer.
  try {
    await PushService.initialiser();
    await GpsService.configurer();
  } catch (e) {
    debugPrint('Initialisation des services : $e');
  }
  runApp(const ProviderScope(child: OnDutyApp()));
}

class OnDutyApp extends ConsumerWidget {
  const OnDutyApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final router = ref.watch(routerProvider);
    final themeMode = ref.watch(themeProvider);
    // Toucher une notification ouvre la course ou la demande concernée.
    PushService.ouvrirRoute = (route) => router.push(route);

    return MaterialApp.router(
      title: 'OnDuty',
      debugShowCheckedModeBanner: false,
      theme: AppTheme.lightTheme,
      darkTheme: AppTheme.darkTheme,
      themeMode: themeMode,
      routerConfig: router,
      localizationsDelegates: const [
        AppLocalizations.delegate,
        GlobalMaterialLocalizations.delegate,
        GlobalWidgetsLocalizations.delegate,
        GlobalCupertinoLocalizations.delegate,
      ],
      supportedLocales: AppLocalizations.supportedLocales,
      localeResolutionCallback: (locale, supportedLocales) {
        if (locale == null) return const Locale('fr');
        for (final supportedLocale in supportedLocales) {
          if (supportedLocale.languageCode == locale.languageCode) {
            return supportedLocale;
          }
        }
        return supportedLocales.first;
      },
    );
  }
}