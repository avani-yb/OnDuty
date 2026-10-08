import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../localization/app_localizations.dart';
import '../../theme/app_colors.dart';

/// Présentation en trois étapes : photo en plein écran, avec le texte, les
/// indicateurs et les boutons posés sur un dégradé marron en bas d'écran.
class BrandingScreen extends StatefulWidget {
  const BrandingScreen({super.key});

  @override
  State<BrandingScreen> createState() => _BrandingScreenState();
}

class _BrandingScreenState extends State<BrandingScreen> {
  static const _images = [
    'assets/images/branding_trajets_vides.jpg',
    'assets/images/branding_paiement.jpg',
    'assets/images/branding_suivi.jpg',
  ];

  final PageController _pageController = PageController();
  int _currentPage = 0;

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _allerA(int page) {
    _pageController.animateToPage(page, duration: const Duration(milliseconds: 300), curve: Curves.easeInOut);
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final etapes = [
      (l10n.brandingStep1, l10n.brandingStep1Desc),
      (l10n.brandingStep2, l10n.brandingStep2Desc),
      (l10n.brandingStep3, l10n.brandingStep3Desc),
    ];
    final derniere = _currentPage == etapes.length - 1;
    final (titre, description) = etapes[_currentPage];

    return Scaffold(
      backgroundColor: Colors.black,
      body: Stack(
        fit: StackFit.expand,
        children: [
          // Photos en plein écran
          PageView.builder(
            controller: _pageController,
            itemCount: _images.length,
            onPageChanged: (index) => setState(() => _currentPage = index),
            itemBuilder: (context, index) => Image.asset(_images[index], fit: BoxFit.cover),
          ),
          // Texte et boutons sur un dégradé, lisibles quelle que soit la photo
          Align(
            alignment: Alignment.bottomCenter,
            child: Container(
              width: double.infinity,
              padding: EdgeInsets.fromLTRB(24, 96, 24, 24 + MediaQuery.of(context).padding.bottom),
              decoration: BoxDecoration(
                gradient: LinearGradient(
                  begin: Alignment.topCenter,
                  end: Alignment.bottomCenter,
                  colors: [
                    AppColors.primaryBrownDark.withValues(alpha: 0),
                    AppColors.primaryBrownDark.withValues(alpha: 0.8),
                    AppColors.primaryBrownDark.withValues(alpha: 0.97),
                  ],
                  stops: const [0, 0.3, 1],
                ),
              ),
              child: Column(
                mainAxisSize: MainAxisSize.min,
                children: [
                  AnimatedSwitcher(
                    duration: const Duration(milliseconds: 250),
                    child: Column(
                      key: ValueKey(_currentPage),
                      children: [
                        Text(
                          titre,
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                                fontWeight: FontWeight.w700,
                                color: Colors.white,
                              ),
                        ),
                        const SizedBox(height: 12),
                        Text(
                          description,
                          textAlign: TextAlign.center,
                          style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                                color: Colors.white.withValues(alpha: 0.92),
                                height: 1.5,
                              ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 24),
                  Row(
                    mainAxisAlignment: MainAxisAlignment.center,
                    children: List.generate(etapes.length, (index) {
                      return AnimatedContainer(
                        duration: const Duration(milliseconds: 300),
                        margin: const EdgeInsets.symmetric(horizontal: 4),
                        width: _currentPage == index ? 24 : 8,
                        height: 8,
                        decoration: BoxDecoration(
                          color: Colors.white.withValues(alpha: _currentPage == index ? 1 : 0.4),
                          borderRadius: BorderRadius.circular(4),
                        ),
                      );
                    }),
                  ),
                  const SizedBox(height: 20),
                  if (derniere)
                    SizedBox(
                      width: double.infinity,
                      child: FilledButton(
                        style: FilledButton.styleFrom(
                          backgroundColor: Colors.white,
                          foregroundColor: AppColors.primaryBrownDark,
                          padding: const EdgeInsets.symmetric(vertical: 16),
                        ),
                        onPressed: () => context.go('/login'),
                        child: Text(l10n.getStarted, style: const TextStyle(fontWeight: FontWeight.w700)),
                      ),
                    )
                  else
                    Row(
                      children: [
                        TextButton(
                          style: TextButton.styleFrom(foregroundColor: Colors.white),
                          onPressed: () => context.go('/login'),
                          child: Text(l10n.skip),
                        ),
                        const Spacer(),
                        FilledButton(
                          style: FilledButton.styleFrom(
                            backgroundColor: Colors.white,
                            foregroundColor: AppColors.primaryBrownDark,
                          ),
                          onPressed: () => _allerA(_currentPage + 1),
                          child: Text(l10n.next),
                        ),
                      ],
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
