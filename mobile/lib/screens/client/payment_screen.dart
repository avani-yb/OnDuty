import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../localization/app_localizations.dart';
import '../../services/payment_service.dart';
import '../../theme/app_colors.dart';
import '../../utils/error_helper.dart';
import '../../utils/formatters.dart';
import '../../widgets/common/custom_text_field.dart';
import '../../widgets/common/primary_button.dart';

/// Paiement d'une course via CamPay (MTN MoMo / Orange Money).
///
/// 1. Détail du montant (prix + commission + frais) et numéro à débiter.
/// 2. CamPay envoie une demande de validation sur le téléphone ; l'écran
///    vérifie régulièrement si elle a été validée.
/// 3. Paiement confirmé : les fonds restent bloqués jusqu'à la livraison.
class PaymentScreen extends ConsumerStatefulWidget {
  // Id de la Course (créée lors de la sélection du transporteur), pas de la Demande.
  final String courseId;

  const PaymentScreen({super.key, required this.courseId});

  @override
  ConsumerState<PaymentScreen> createState() => _PaymentScreenState();
}

class _PaymentScreenState extends ConsumerState<PaymentScreen> {
  static const _intervalle = Duration(seconds: 5);
  static const _verificationsMax = 36; // environ 3 minutes

  final _formKey = GlobalKey<FormState>();
  final _numero = TextEditingController();
  Devis? _devis;
  Paiement? _paiement;
  bool _isLoading = true;
  bool _isPaying = false;
  Timer? _minuteur;
  int _verifications = 0;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _minuteur?.cancel();
    _numero.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final service = ref.read(paymentServiceProvider);
    try {
      final paiement = await service.getPaiementCourse(widget.courseId);
      Devis? devis;
      if (paiement == null || paiement.echoue) {
        devis = await service.getDevis(widget.courseId);
        _numero.text = devis.numeroDefaut;
      }
      if (!mounted) return;
      setState(() {
        _paiement = paiement;
        _devis = devis;
      });
      if (paiement != null && paiement.enAttente) _demarrerVerification();
    } catch (e) {
      _erreur(e);
    } finally {
      if (mounted) setState(() => _isLoading = false);
    }
  }

  void _erreur(Object e) {
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text(friendlyError(e)), backgroundColor: AppColors.error),
    );
  }

  Future<void> _payer() async {
    if (!_formKey.currentState!.validate()) return;
    setState(() => _isPaying = true);
    try {
      final paiement = await ref.read(paymentServiceProvider).payer(
            courseId: widget.courseId,
            numero: _numero.text.trim(),
          );
      if (!mounted) return;
      setState(() => _paiement = paiement);
      _demarrerVerification();
    } catch (e) {
      _erreur(e);
    } finally {
      if (mounted) setState(() => _isPaying = false);
    }
  }

  void _demarrerVerification() {
    _minuteur?.cancel();
    _verifications = 0;
    _minuteur = Timer.periodic(_intervalle, (_) => _verifier());
  }

  Future<void> _verifier() async {
    final paiement = _paiement;
    if (paiement == null || !paiement.enAttente) {
      _minuteur?.cancel();
      return;
    }
    _verifications++;
    if (_verifications > _verificationsMax) {
      _minuteur?.cancel();
      if (mounted) setState(() {});
      return;
    }
    try {
      final mis = await ref.read(paymentServiceProvider).verifier(paiement.id);
      if (!mounted) return;
      setState(() => _paiement = mis);
      if (!mis.enAttente) {
        _minuteur?.cancel();
        if (mis.echoue) {
          final devis = await ref.read(paymentServiceProvider).getDevis(widget.courseId);
          if (mounted) setState(() => _devis = devis);
        }
      }
    } catch (_) {
      // Erreur réseau ponctuelle : on réessaiera au prochain passage.
    }
  }

  /// Vérifie tout de suite, et relance la vérification automatique si elle
  /// s'était arrêtée (délai dépassé).
  Future<void> _verifierMaintenant() async {
    _demarrerVerification();
    setState(() {});
    await _verifier();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final paiement = _paiement;

    Widget contenu;
    if (_isLoading) {
      contenu = const Center(child: CircularProgressIndicator());
    } else if (paiement != null && paiement.estPaye) {
      contenu = _resultat(
        l10n,
        icone: Icons.verified,
        couleur: AppColors.success,
        titre: l10n.paymentDone,
        texte: l10n.paymentDoneBody,
      );
    } else if (paiement != null && paiement.statut == 'rembourse') {
      contenu = _resultat(l10n, icone: Icons.undo, couleur: Colors.grey, titre: l10n.paymentRefunded, texte: '');
    } else if (paiement != null && paiement.enAttente) {
      contenu = _attente(l10n, paiement);
    } else {
      contenu = _formulaire(l10n);
    }

    return Scaffold(appBar: AppBar(title: Text(l10n.payment)), body: contenu);
  }

  Widget _formulaire(AppLocalizations l10n) {
    final devis = _devis;
    if (devis == null) return Center(child: Text(l10n.error));
    final echec = _paiement?.echoue == true;

    return Form(
      key: _formKey,
      child: ListView(
        padding: const EdgeInsets.all(16),
        children: [
          if (echec)
            Card(
              color: AppColors.error.withValues(alpha: 0.08),
              child: Padding(
                padding: const EdgeInsets.all(16),
                child: Text(
                  _paiement!.messageErreur.isEmpty ? l10n.paymentFailed : '${l10n.paymentFailed} : ${_paiement!.messageErreur}',
                  style: const TextStyle(color: AppColors.error),
                ),
              ),
            ),
          Card(
            child: Padding(
              padding: const EdgeInsets.all(16),
              child: Column(
                children: [
                  _Montant(l10n.tripPrice, devis.montantCourse),
                  _Montant(l10n.onDutyCommission(devis.tauxCommission.round().toString()), devis.commission),
                  _Montant(l10n.paymentFees, devis.frais),
                  const Divider(height: 24),
                  _Montant(l10n.totalToPay, devis.total, gras: true),
                ],
              ),
            ),
          ),
          const SizedBox(height: 16),
          CustomTextField(
            controller: _numero,
            label: l10n.mobileMoneyNumber,
            hint: '6XXXXXXXX',
            keyboardType: TextInputType.phone,
            prefixIcon: Icons.phone_android,
            validator: (v) {
              final chiffres = (v ?? '').replaceAll(RegExp(r'\D'), '');
              final local = chiffres.startsWith('237') ? chiffres.substring(3) : chiffres;
              return RegExp(r'^6\d{8}$').hasMatch(local) ? null : l10n.invalidMobileMoneyNumber;
            },
          ),
          const SizedBox(height: 8),
          Text(l10n.mobileMoneyHint, style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 24),
          PrimaryButton(
            text: l10n.payAmount(formatFcfa(devis.total)),
            onPressed: _isPaying ? null : _payer,
            isLoading: _isPaying,
          ),
          const SizedBox(height: 16),
          Text(
            l10n.escrowInfo,
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.bodySmall,
          ),
        ],
      ),
    );
  }

  Widget _attente(AppLocalizations l10n, Paiement paiement) {
    final delaiDepasse = _verifications > _verificationsMax;
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        const SizedBox(height: 24),
        if (!delaiDepasse) const Center(child: CircularProgressIndicator()),
        if (delaiDepasse) const Icon(Icons.hourglass_bottom, size: 64, color: AppColors.warning),
        const SizedBox(height: 24),
        Text(
          l10n.validateOnPhone,
          textAlign: TextAlign.center,
          style: Theme.of(context).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
        ),
        const SizedBox(height: 12),
        Text(
          paiement.codeUssd.isEmpty ? l10n.validateOnPhoneBody : l10n.validateOnPhoneUssd(paiement.codeUssd),
          textAlign: TextAlign.center,
        ),
        if (paiement.montant != null) ...[
          const SizedBox(height: 12),
          Text(
            formatFcfa(paiement.montant),
            textAlign: TextAlign.center,
            style: Theme.of(context).textTheme.headlineSmall?.copyWith(color: AppColors.primaryBrown),
          ),
        ],
        if (delaiDepasse) ...[
          const SizedBox(height: 12),
          Text(l10n.paymentStillPending, textAlign: TextAlign.center),
        ],
        const SizedBox(height: 24),
        OutlinedButton.icon(
          onPressed: _verifierMaintenant,
          icon: const Icon(Icons.refresh),
          label: Text(l10n.iValidatedCheck),
        ),
      ],
    );
  }

  Widget _resultat(AppLocalizations l10n,
      {required IconData icone, required Color couleur, required String titre, required String texte}) {
    return Padding(
      padding: const EdgeInsets.all(24),
      child: Column(
        mainAxisAlignment: MainAxisAlignment.center,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          Icon(icone, size: 80, color: couleur),
          const SizedBox(height: 24),
          Text(titre,
              textAlign: TextAlign.center,
              style: Theme.of(context).textTheme.headlineSmall?.copyWith(fontWeight: FontWeight.w700)),
          const SizedBox(height: 12),
          Text(texte, textAlign: TextAlign.center),
          const SizedBox(height: 32),
          PrimaryButton(text: l10n.backToCourse, onPressed: () => context.pop()),
        ],
      ),
    );
  }
}

class _Montant extends StatelessWidget {
  final String label;
  final double montant;
  final bool gras;

  const _Montant(this.label, this.montant, {this.gras = false});

  @override
  Widget build(BuildContext context) {
    final style = gras
        ? Theme.of(context).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700, color: AppColors.primaryBrown)
        : Theme.of(context).textTheme.bodyMedium;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 4),
      child: Row(
        children: [
          Expanded(child: Text(label, style: style)),
          Text(formatFcfa(montant), style: style),
        ],
      ),
    );
  }
}
