import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';

/// Une étape de la présentation : photo en plein écran, texte posé sur une
/// zone marron en dégradé pour rester lisible quelle que soit la photo.
class BrandingStep extends StatelessWidget {
  final String title;
  final String description;
  final String image;

  const BrandingStep({
    super.key,
    required this.title,
    required this.description,
    required this.image,
  });

  @override
  Widget build(BuildContext context) {
    return Stack(
      fit: StackFit.expand,
      children: [
        Image.asset(image, fit: BoxFit.cover),
        Align(
          alignment: Alignment.bottomCenter,
          child: Container(
            width: double.infinity,
            padding: const EdgeInsets.fromLTRB(28, 64, 28, 32),
            decoration: BoxDecoration(
              gradient: LinearGradient(
                begin: Alignment.topCenter,
                end: Alignment.bottomCenter,
                colors: [
                  AppColors.primaryBrownDark.withValues(alpha: 0),
                  AppColors.primaryBrownDark.withValues(alpha: 0.75),
                  AppColors.primaryBrownDark.withValues(alpha: 0.95),
                ],
                stops: const [0, 0.35, 1],
              ),
            ),
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                Text(
                  title,
                  style: Theme.of(context).textTheme.headlineMedium?.copyWith(
                        fontWeight: FontWeight.w700,
                        color: Colors.white,
                      ),
                  textAlign: TextAlign.center,
                ),
                const SizedBox(height: 12),
                Text(
                  description,
                  style: Theme.of(context).textTheme.bodyLarge?.copyWith(
                        color: Colors.white.withValues(alpha: 0.92),
                        height: 1.5,
                      ),
                  textAlign: TextAlign.center,
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }
}
