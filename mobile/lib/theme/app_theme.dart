import 'package:flutter/material.dart';
import 'app_colors.dart';

class AppTheme {
  static ThemeData get lightTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.light,
      colorScheme: ColorScheme.light(
        primary: AppColors.primaryBrown,
        secondary: AppColors.accentBrown,
        surface: AppColors.lightSurface,
        background: AppColors.lightBackground,
        onPrimary: Colors.white,
        onSecondary: Colors.white,
        onSurface: AppColors.lightPrimaryText,
        onBackground: AppColors.lightPrimaryText,
        error: AppColors.error,
        onError: Colors.white,
      ),
      scaffoldBackgroundColor: AppColors.lightBackground,
      appBarTheme: AppBarTheme(
        backgroundColor: AppColors.lightSurface,
        foregroundColor: AppColors.lightPrimaryText,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: const TextStyle(
          fontFamily: 'Inter',
          fontSize: 20,
          fontWeight: FontWeight.w600,
          color: AppColors.lightPrimaryText,
        ),
        iconTheme: const IconThemeData(color: AppColors.lightPrimaryText),
      ),
      cardTheme: CardThemeData(
        color: AppColors.lightSurface,
        elevation: 1,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: AppColors.lightDivider, width: 1),
        ),
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primaryBrown,
          foregroundColor: Colors.white,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(
            fontFamily: 'Inter',
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.primaryBrown,
          side: const BorderSide(color: AppColors.primaryBrown, width: 1.5),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(
            fontFamily: 'Inter',
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.primaryBrown,
          textStyle: const TextStyle(
            fontFamily: 'Inter',
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.lightSurface,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.lightDivider),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.lightDivider),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.primaryBrown, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.error),
        ),
        labelStyle: const TextStyle(
          fontFamily: 'Inter',
          color: AppColors.lightSecondaryText,
        ),
        hintStyle: const TextStyle(
          fontFamily: 'Inter',
          color: AppColors.lightSecondaryText,
        ),
      ),
      textTheme: const TextTheme(
        displayLarge: TextStyle(fontFamily: 'Inter', fontSize: 32, fontWeight: FontWeight.w700, color: AppColors.lightPrimaryText),
        displayMedium: TextStyle(fontFamily: 'Inter', fontSize: 28, fontWeight: FontWeight.w600, color: AppColors.lightPrimaryText),
        displaySmall: TextStyle(fontFamily: 'Inter', fontSize: 24, fontWeight: FontWeight.w600, color: AppColors.lightPrimaryText),
        headlineLarge: TextStyle(fontFamily: 'Inter', fontSize: 22, fontWeight: FontWeight.w600, color: AppColors.lightPrimaryText),
        headlineMedium: TextStyle(fontFamily: 'Inter', fontSize: 20, fontWeight: FontWeight.w600, color: AppColors.lightPrimaryText),
        headlineSmall: TextStyle(fontFamily: 'Inter', fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.lightPrimaryText),
        titleLarge: TextStyle(fontFamily: 'Inter', fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.lightPrimaryText),
        titleMedium: TextStyle(fontFamily: 'Inter', fontSize: 14, fontWeight: FontWeight.w500, color: AppColors.lightPrimaryText),
        titleSmall: TextStyle(fontFamily: 'Inter', fontSize: 12, fontWeight: FontWeight.w500, color: AppColors.lightPrimaryText),
        bodyLarge: TextStyle(fontFamily: 'Inter', fontSize: 16, fontWeight: FontWeight.w400, color: AppColors.lightPrimaryText),
        bodyMedium: TextStyle(fontFamily: 'Inter', fontSize: 14, fontWeight: FontWeight.w400, color: AppColors.lightPrimaryText),
        bodySmall: TextStyle(fontFamily: 'Inter', fontSize: 12, fontWeight: FontWeight.w400, color: AppColors.lightSecondaryText),
        labelLarge: TextStyle(fontFamily: 'Inter', fontSize: 14, fontWeight: FontWeight.w500, color: AppColors.lightPrimaryText),
        labelMedium: TextStyle(fontFamily: 'Inter', fontSize: 12, fontWeight: FontWeight.w500, color: AppColors.lightPrimaryText),
        labelSmall: TextStyle(fontFamily: 'Inter', fontSize: 11, fontWeight: FontWeight.w400, color: AppColors.lightSecondaryText),
      ),
      dividerTheme: const DividerThemeData(
        color: AppColors.lightDivider,
        thickness: 1,
        space: 1,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: AppColors.lightSurface,
        selectedColor: AppColors.primaryBrown.withOpacity(0.1),
        labelStyle: const TextStyle(fontFamily: 'Inter', color: AppColors.lightPrimaryText),
        side: const BorderSide(color: AppColors.lightDivider),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: AppColors.lightSurface,
        selectedItemColor: AppColors.primaryBrown,
        unselectedItemColor: AppColors.lightSecondaryText,
        type: BottomNavigationBarType.fixed,
        elevation: 8,
        selectedLabelStyle: const TextStyle(fontFamily: 'Inter', fontSize: 12, fontWeight: FontWeight.w500),
        unselectedLabelStyle: const TextStyle(fontFamily: 'Inter', fontSize: 12, fontWeight: FontWeight.w400),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: AppColors.primaryBrown,
        foregroundColor: Colors.white,
        elevation: 4,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: AppColors.lightSurface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        titleTextStyle: const TextStyle(fontFamily: 'Inter', fontSize: 20, fontWeight: FontWeight.w600, color: AppColors.lightPrimaryText),
        contentTextStyle: const TextStyle(fontFamily: 'Inter', fontSize: 16, color: AppColors.lightPrimaryText),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: AppColors.lightSurface,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        modalBackgroundColor: AppColors.lightSurface,
      ),
    );
  }

  static ThemeData get darkTheme {
    return ThemeData(
      useMaterial3: true,
      brightness: Brightness.dark,
      colorScheme: ColorScheme.dark(
        primary: AppColors.primaryBrownLight,
        secondary: AppColors.accentBrown,
        surface: AppColors.darkSurface,
        background: AppColors.darkBackground,
        onPrimary: Colors.black,
        onSecondary: Colors.black,
        onSurface: AppColors.darkPrimaryText,
        onBackground: AppColors.darkPrimaryText,
        error: AppColors.error,
        onError: Colors.black,
      ),
      scaffoldBackgroundColor: AppColors.darkBackground,
      appBarTheme: AppBarTheme(
        backgroundColor: AppColors.darkSurface,
        foregroundColor: AppColors.darkPrimaryText,
        elevation: 0,
        centerTitle: true,
        titleTextStyle: const TextStyle(
          fontFamily: 'Inter',
          fontSize: 20,
          fontWeight: FontWeight.w600,
          color: AppColors.darkPrimaryText,
        ),
        iconTheme: const IconThemeData(color: AppColors.darkPrimaryText),
      ),
      cardTheme: CardThemeData(
        color: AppColors.darkSurface,
        elevation: 1,
        shape: RoundedRectangleBorder(
          borderRadius: BorderRadius.circular(16),
          side: const BorderSide(color: AppColors.darkDivider, width: 1),
        ),
        margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
      ),
      elevatedButtonTheme: ElevatedButtonThemeData(
        style: ElevatedButton.styleFrom(
          backgroundColor: AppColors.primaryBrownLight,
          foregroundColor: Colors.black,
          elevation: 0,
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(
            fontFamily: 'Inter',
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      outlinedButtonTheme: OutlinedButtonThemeData(
        style: OutlinedButton.styleFrom(
          foregroundColor: AppColors.primaryBrownLight,
          side: const BorderSide(color: AppColors.primaryBrownLight, width: 1.5),
          padding: const EdgeInsets.symmetric(horizontal: 24, vertical: 16),
          shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(12)),
          textStyle: const TextStyle(
            fontFamily: 'Inter',
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      textButtonTheme: TextButtonThemeData(
        style: TextButton.styleFrom(
          foregroundColor: AppColors.primaryBrownLight,
          textStyle: const TextStyle(
            fontFamily: 'Inter',
            fontSize: 16,
            fontWeight: FontWeight.w600,
          ),
        ),
      ),
      inputDecorationTheme: InputDecorationTheme(
        filled: true,
        fillColor: AppColors.darkSurface,
        contentPadding: const EdgeInsets.symmetric(horizontal: 16, vertical: 16),
        border: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.darkDivider),
        ),
        enabledBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.darkDivider),
        ),
        focusedBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.primaryBrownLight, width: 2),
        ),
        errorBorder: OutlineInputBorder(
          borderRadius: BorderRadius.circular(12),
          borderSide: const BorderSide(color: AppColors.error),
        ),
        labelStyle: const TextStyle(
          fontFamily: 'Inter',
          color: AppColors.darkSecondaryText,
        ),
        hintStyle: const TextStyle(
          fontFamily: 'Inter',
          color: AppColors.darkSecondaryText,
        ),
      ),
      textTheme: const TextTheme(
        displayLarge: TextStyle(fontFamily: 'Inter', fontSize: 32, fontWeight: FontWeight.w700, color: AppColors.darkPrimaryText),
        displayMedium: TextStyle(fontFamily: 'Inter', fontSize: 28, fontWeight: FontWeight.w600, color: AppColors.darkPrimaryText),
        displaySmall: TextStyle(fontFamily: 'Inter', fontSize: 24, fontWeight: FontWeight.w600, color: AppColors.darkPrimaryText),
        headlineLarge: TextStyle(fontFamily: 'Inter', fontSize: 22, fontWeight: FontWeight.w600, color: AppColors.darkPrimaryText),
        headlineMedium: TextStyle(fontFamily: 'Inter', fontSize: 20, fontWeight: FontWeight.w600, color: AppColors.darkPrimaryText),
        headlineSmall: TextStyle(fontFamily: 'Inter', fontSize: 18, fontWeight: FontWeight.w600, color: AppColors.darkPrimaryText),
        titleLarge: TextStyle(fontFamily: 'Inter', fontSize: 16, fontWeight: FontWeight.w600, color: AppColors.darkPrimaryText),
        titleMedium: TextStyle(fontFamily: 'Inter', fontSize: 14, fontWeight: FontWeight.w500, color: AppColors.darkPrimaryText),
        titleSmall: TextStyle(fontFamily: 'Inter', fontSize: 12, fontWeight: FontWeight.w500, color: AppColors.darkPrimaryText),
        bodyLarge: TextStyle(fontFamily: 'Inter', fontSize: 16, fontWeight: FontWeight.w400, color: AppColors.darkPrimaryText),
        bodyMedium: TextStyle(fontFamily: 'Inter', fontSize: 14, fontWeight: FontWeight.w400, color: AppColors.darkPrimaryText),
        bodySmall: TextStyle(fontFamily: 'Inter', fontSize: 12, fontWeight: FontWeight.w400, color: AppColors.darkSecondaryText),
        labelLarge: TextStyle(fontFamily: 'Inter', fontSize: 14, fontWeight: FontWeight.w500, color: AppColors.darkPrimaryText),
        labelMedium: TextStyle(fontFamily: 'Inter', fontSize: 12, fontWeight: FontWeight.w500, color: AppColors.darkPrimaryText),
        labelSmall: TextStyle(fontFamily: 'Inter', fontSize: 11, fontWeight: FontWeight.w400, color: AppColors.darkSecondaryText),
      ),
      dividerTheme: const DividerThemeData(
        color: AppColors.darkDivider,
        thickness: 1,
        space: 1,
      ),
      chipTheme: ChipThemeData(
        backgroundColor: AppColors.darkSurface,
        selectedColor: AppColors.primaryBrownLight.withOpacity(0.2),
        labelStyle: const TextStyle(fontFamily: 'Inter', color: AppColors.darkPrimaryText),
        side: const BorderSide(color: AppColors.darkDivider),
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
      ),
      bottomNavigationBarTheme: BottomNavigationBarThemeData(
        backgroundColor: AppColors.darkSurface,
        selectedItemColor: AppColors.primaryBrownLight,
        unselectedItemColor: AppColors.darkSecondaryText,
        type: BottomNavigationBarType.fixed,
        elevation: 8,
        selectedLabelStyle: const TextStyle(fontFamily: 'Inter', fontSize: 12, fontWeight: FontWeight.w500),
        unselectedLabelStyle: const TextStyle(fontFamily: 'Inter', fontSize: 12, fontWeight: FontWeight.w400),
      ),
      floatingActionButtonTheme: FloatingActionButtonThemeData(
        backgroundColor: AppColors.primaryBrownLight,
        foregroundColor: Colors.black,
        elevation: 4,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      ),
      dialogTheme: DialogThemeData(
        backgroundColor: AppColors.darkSurface,
        shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(20)),
        titleTextStyle: const TextStyle(fontFamily: 'Inter', fontSize: 20, fontWeight: FontWeight.w600, color: AppColors.darkPrimaryText),
        contentTextStyle: const TextStyle(fontFamily: 'Inter', fontSize: 16, color: AppColors.darkPrimaryText),
      ),
      bottomSheetTheme: BottomSheetThemeData(
        backgroundColor: AppColors.darkSurface,
        shape: const RoundedRectangleBorder(borderRadius: BorderRadius.vertical(top: Radius.circular(24))),
        modalBackgroundColor: AppColors.darkSurface,
      ),
    );
  }
}