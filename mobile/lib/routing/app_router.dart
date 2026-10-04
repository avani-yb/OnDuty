import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../screens/onboarding/branding_screen.dart';
import '../screens/auth/login_screen.dart';
import '../screens/auth/register_screen.dart';
import '../screens/client/home_screen.dart';
import '../screens/client/activity_screen.dart';
import '../screens/transporter/trips_screen.dart';
import '../screens/shared/profile_screen.dart';
import '../screens/auth/forgot_password_screen.dart';
import '../screens/client/new_shipment_screen.dart';
import '../screens/transporter/new_trip_screen.dart';
import '../screens/shared/settings_screen.dart';
import '../screens/client/shipment_detail_screen.dart';
import '../screens/transporter/trip_detail_screen.dart';
import '../screens/client/matching_screen.dart';
import '../screens/transporter/matching_trips_screen.dart';
import '../screens/shared/verification_screen.dart';
import '../screens/shared/become_transporter_screen.dart';
import '../screens/shared/payment_history_screen.dart';
import '../screens/client/payment_screen.dart';
import '../screens/shared/tracking_screen.dart';
import '../screens/shared/notifications_screen.dart';
import '../screens/client/ai_success_screen.dart';
import '../screens/client/demande_detail_screen.dart';
import '../screens/client/edit_demande_screen.dart';
import '../services/auth_service.dart';

// Routes accessibles sans être connecté.
const _publicRoutes = ['/branding', '/login', '/register', '/forgot-password'];

final routerProvider = Provider<GoRouter>((ref) {
  final authService = ref.watch(authServiceProvider);

  return GoRouter(
    initialLocation: '/branding',
    redirect: (context, state) async {
      final loggedIn = await authService.isLoggedIn();
      final isPublicRoute = _publicRoutes.contains(state.matchedLocation);

      if (!loggedIn && !isPublicRoute) {
        return '/login';
      }
      if (loggedIn && (state.matchedLocation == '/login' || state.matchedLocation == '/register')) {
        return '/home';
      }
      // Un utilisateur déjà connecté qui relance l'app n'a pas besoin de
      // revoir le carrousel de présentation à chaque démarrage.
      if (loggedIn && state.matchedLocation == '/branding') {
        return '/home';
      }
      return null;
    },
    routes: [
      GoRoute(
        path: '/branding',
        builder: (context, state) => const BrandingScreen(),
      ),
      GoRoute(
        path: '/login',
        builder: (context, state) => const LoginScreen(),
      ),
      GoRoute(
        path: '/register',
        builder: (context, state) => const RegisterScreen(),
      ),
      GoRoute(
        path: '/forgot-password',
        builder: (context, state) => const ForgotPasswordScreen(),
      ),
      GoRoute(
        path: '/home',
        builder: (context, state) => const HomeScreen(),
      ),
      GoRoute(
        path: '/activity',
        builder: (context, state) => const ActivityScreen(),
      ),
      GoRoute(
        path: '/trips',
        builder: (context, state) => const TripsScreen(),
      ),
      GoRoute(
        path: '/profile',
        builder: (context, state) => const ProfileScreen(),
      ),
      GoRoute(
        path: '/settings',
        builder: (context, state) => const SettingsScreen(),
      ),
      GoRoute(
        path: '/new-shipment',
        builder: (context, state) => const NewShipmentScreen(),
      ),
      GoRoute(
        path: '/new-trip',
        builder: (context, state) => const NewTripScreen(),
      ),
      GoRoute(
        path: '/become-transporter',
        builder: (context, state) => const BecomeTransporterScreen(),
      ),
      GoRoute(
        path: '/payment-history',
        builder: (context, state) => const PaymentHistoryScreen(),
      ),
      // :id est ici l'id de la Course (demande déjà matchée à un trajet).
      GoRoute(
        path: '/shipment/:id',
        builder: (context, state) => ShipmentDetailScreen(courseId: state.pathParameters['id']!),
      ),
      GoRoute(
        path: '/trip/:id',
        builder: (context, state) => TripDetailScreen(tripId: state.pathParameters['id']!),
      ),
      // :shipmentId ici est bien l'id de la Demande (avant matching/sélection).
      GoRoute(
        path: '/matching/:shipmentId',
        builder: (context, state) => MatchingScreen(shipmentId: state.pathParameters['shipmentId']!),
      ),
      GoRoute(
        path: '/matching-trips/:tripId',
        builder: (context, state) => MatchingTripsScreen(tripId: state.pathParameters['tripId']!),
      ),
      GoRoute(
        path: '/verification',
        builder: (context, state) => const VerificationScreen(),
      ),
      // :courseId ici est l'id de la Course, créée lors de la sélection du transporteur.
      GoRoute(
        path: '/payment/:courseId',
        builder: (context, state) => PaymentScreen(courseId: state.pathParameters['courseId']!),
      ),
      GoRoute(
        path: '/tracking/:courseId',
        builder: (context, state) => TrackingScreen(courseId: state.pathParameters['courseId']!),
      ),
      GoRoute(
        path: '/notifications',
        builder: (context, state) => const NotificationsScreen(),
      ),
      // :id est ici l'id de la Demande (« Mes demandes »).
      GoRoute(
        path: '/demande/:id',
        builder: (context, state) => DemandeDetailScreen(demandeId: state.pathParameters['id']!),
        routes: [
          GoRoute(
            path: 'modifier',
            builder: (context, state) => EditDemandeScreen(demandeId: state.pathParameters['id']!),
          ),
          GoRoute(
            path: 'succes',
            builder: (context, state) => AiSuccessScreen(demandeId: state.pathParameters['id']!),
          ),
        ],
      ),
    ],
    errorBuilder: (context, state) => Scaffold(
      body: Center(
        child: Text('Page non trouvée: ${state.error}'),
      ),
    ),
  );
});
