// This is a basic Flutter widget test.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:onduty/main.dart';

void main() {
  testWidgets('App starts correctly', (WidgetTester tester) async {
    // Build our app and trigger a frame.
    await tester.pumpWidget(const ProviderScope(child: OnDutyApp()));

    // Wait for the first frame to render the PageView
    await tester.pumpAndSettle();

    // Verify that the app starts correctly - just check that something is rendered
    expect(find.byType(Scaffold), findsOneWidget);
  });
}