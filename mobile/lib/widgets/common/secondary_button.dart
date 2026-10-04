import 'package:flutter/material.dart';

import '../../theme/app_colors.dart';

class SecondaryButton extends StatelessWidget {
  final String text;
  final VoidCallback? onPressed;
  final bool isLoading;
  final bool fullWidth;
  final Color? foregroundColor;

  const SecondaryButton({
    super.key,
    required this.text,
    this.onPressed,
    this.isLoading = false,
    this.fullWidth = true,
    this.foregroundColor,
  });

  @override
  Widget build(BuildContext context) {
    final button = OutlinedButton(
      onPressed: isLoading ? null : onPressed,
      style: OutlinedButton.styleFrom(
        foregroundColor: foregroundColor ?? AppColors.primaryBrown,
        side: BorderSide(color: foregroundColor ?? AppColors.primaryBrown, width: 1.5),
        padding: const EdgeInsets.symmetric(vertical: 16),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
      ),
      child: isLoading
          ? SizedBox(
              width: 24,
              height: 24,
              child: CircularProgressIndicator(
                strokeWidth: 2,
                valueColor: AlwaysStoppedAnimation<Color>(foregroundColor ?? AppColors.primaryBrown),
              ),
            )
          : Text(
              text,
              style: const TextStyle(
                fontFamily: 'Inter',
                fontSize: 16,
                fontWeight: FontWeight.w600,
              ),
            ),
    );

    return fullWidth ? SizedBox(width: double.infinity, child: button) : button;
  }
}