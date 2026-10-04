import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../../localization/app_localizations.dart';
import '../../theme/app_colors.dart';
import '../../widgets/common/branding_step.dart';

class BrandingScreen extends StatefulWidget {
  const BrandingScreen({super.key});

  @override
  State<BrandingScreen> createState() => _BrandingScreenState();
}

class _BrandingScreenState extends State<BrandingScreen> {
  final PageController _pageController = PageController();
  int _currentPage = 0;

  @override
  void dispose() {
    _pageController.dispose();
    super.dispose();
  }

  void _nextPage() {
    if (_currentPage < 2) {
      _pageController.nextPage(
        duration: const Duration(milliseconds: 300),
        curve: Curves.easeInOut,
      );
    } else {
      context.go('/login');
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    return Scaffold(
      backgroundColor: Theme.of(context).scaffoldBackgroundColor,
      body: SafeArea(
        top: false,
        child: Column(
          children: [
            Expanded(
              child: PageView(
                controller: _pageController,
                onPageChanged: (index) => setState(() => _currentPage = index),
                children: [
                  BrandingStep(
                    title: l10n.brandingStep1,
                    description: l10n.brandingStep1Desc,
                    image: 'assets/images/branding_trajets_vides.png',
                  ),
                  BrandingStep(
                    title: l10n.brandingStep2,
                    description: l10n.brandingStep2Desc,
                    image: 'assets/images/branding_paiement.png',
                  ),
                  BrandingStep(
                    title: l10n.brandingStep3,
                    description: l10n.brandingStep3Desc,
                    image: 'assets/images/branding_suivi.png',
                  ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(24),
              child: Column(
                children: [
                  Row(
                    mainAxisAlignment: _currentPage == 2
                        ? MainAxisAlignment.center
                        : MainAxisAlignment.spaceBetween,
                    children: [
                      if (_currentPage > 0)
                        TextButton(
                          onPressed: () => _pageController.previousPage(
                            duration: const Duration(milliseconds: 300),
                            curve: Curves.easeInOut,
                          ),
                          child: Text(AppLocalizations.of(context).back),
                        )
                      else
                        const SizedBox(width: 80),
                      Row(
                        mainAxisSize: MainAxisSize.min,
                        children: List.generate(3, (index) {
                          return AnimatedContainer(
                            duration: const Duration(milliseconds: 300),
                            margin: const EdgeInsets.symmetric(horizontal: 4),
                            width: _currentPage == index ? 24 : 8,
                            height: 8,
                            decoration: BoxDecoration(
                              color: _currentPage == index
                                  ? AppColors.primaryBrown
                                  : AppColors.lightDivider,
                              borderRadius: BorderRadius.circular(4),
                            ),
                          );
                        }),
                      ),
                      if (_currentPage < 2)
                        TextButton(
                          onPressed: () => context.go('/login'),
                          child: Text(AppLocalizations.of(context).skip),
                        )
                      else
                        const SizedBox(width: 80),
                    ],
                  ),
                  const SizedBox(height: 16),
                  if (_currentPage == 2)
                    SizedBox(
                      width: double.infinity,
                      child: ElevatedButton(
                        onPressed: _nextPage,
                        child: Text(AppLocalizations.of(context).getStarted),
                      ),
                    ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}