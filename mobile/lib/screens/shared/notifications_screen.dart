import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../localization/app_localizations.dart';
import '../../services/notification_service.dart';
import '../../theme/app_colors.dart';
import '../../utils/error_helper.dart';
import '../../utils/formatters.dart';

/// Notifications reçues (course choisie, paiement, incident, litige...).
/// Toucher une notification ouvre la course ou la demande concernée.
class NotificationsScreen extends ConsumerStatefulWidget {
  const NotificationsScreen({super.key});

  @override
  ConsumerState<NotificationsScreen> createState() => _NotificationsScreenState();
}

class _NotificationsScreenState extends ConsumerState<NotificationsScreen> {
  List<AppNotification> _notifications = [];
  bool _isLoading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final notifications = await ref.read(notificationServiceProvider).getNotifications();
      if (mounted) {
        setState(() {
          _notifications = notifications;
          _error = null;
        });
      }
    } catch (e) {
      if (mounted) setState(() => _error = friendlyError(e));
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  Future<void> _toutMarquerLu() async {
    try {
      await ref.read(notificationServiceProvider).toutMarquerLu();
      await _load();
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text(friendlyError(e)), backgroundColor: AppColors.error),
        );
      }
    }
  }

  Future<void> _ouvrir(AppNotification notification) async {
    if (!notification.lue) {
      // Sans attendre : l'ouverture ne doit pas dépendre du réseau.
      ref.read(notificationServiceProvider).marquerLue(notification.id).catchError((_) {});
    }
    final String? route = notification.courseId != null
        ? '/shipment/${notification.courseId}'
        : notification.demandeId != null
            ? '/demande/${notification.demandeId}'
            : notification.trajetId != null
                ? '/trip/${notification.trajetId}'
                : null;
    if (route != null) await context.push(route);
    if (mounted) _load();
  }

  IconData _icone(String type) {
    switch (type) {
      case 'paiement':
        return Icons.payments_outlined;
      case 'incident':
        return Icons.report_problem_outlined;
      case 'litige':
        return Icons.gavel_outlined;
      case 'matching':
        return Icons.handshake_outlined;
      case 'controle_ia':
        return Icons.smart_toy_outlined;
      case 'kyc':
        return Icons.verified_user_outlined;
      default:
        return Icons.local_shipping_outlined;
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);

    Widget body;
    if (_isLoading) {
      body = const Center(child: CircularProgressIndicator());
    } else if (_error != null) {
      body = Center(child: Text(_error!));
    } else if (_notifications.isEmpty) {
      body = Center(
        child: Column(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(Icons.notifications_none, size: 80, color: AppColors.primaryBrown.withValues(alpha: 0.3)),
            const SizedBox(height: 16),
            Text(l10n.noNotifications, style: Theme.of(context).textTheme.bodyLarge),
          ],
        ),
      );
    } else {
      body = RefreshIndicator(
        onRefresh: _load,
        child: ListView.separated(
          padding: const EdgeInsets.symmetric(vertical: 8),
          itemCount: _notifications.length,
          separatorBuilder: (_, _) => const Divider(height: 1),
          itemBuilder: (context, index) {
            final notification = _notifications[index];
            final couleur = notification.lue ? Colors.grey : AppColors.primaryBrown;
            return ListTile(
              onTap: () => _ouvrir(notification),
              tileColor: notification.lue ? null : AppColors.primaryBrown.withValues(alpha: 0.05),
              leading: CircleAvatar(
                backgroundColor: couleur.withValues(alpha: 0.12),
                child: Icon(_icone(notification.type), color: couleur),
              ),
              title: Text(
                notification.titre,
                style: TextStyle(fontWeight: notification.lue ? FontWeight.w500 : FontWeight.w700),
              ),
              subtitle: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  const SizedBox(height: 4),
                  Text(notification.corps),
                  const SizedBox(height: 4),
                  Text(
                    formatDateHeure(notification.date),
                    style: Theme.of(context).textTheme.bodySmall,
                  ),
                ],
              ),
              isThreeLine: true,
            );
          },
        ),
      );
    }

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.notifications),
        actions: [
          if (_notifications.any((n) => !n.lue))
            TextButton(onPressed: _toutMarquerLu, child: Text(l10n.markAllRead)),
        ],
      ),
      body: body,
    );
  }
}
