import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

/// Revient à l'écran précédent s'il y en a un dans la pile de navigation,
/// sinon retombe sur l'accueil. Utile pour les boutons "Retour"/"Annuler"
/// d'un écran qui peut être atteint à la fois via `push` (une page précédente
/// existe) et via `go` (la pile a été remplacée, rien à dépiler) — un simple
/// `context.pop()` fermerait l'application dans ce second cas.
void safePop(BuildContext context) {
  if (context.canPop()) {
    context.pop();
  } else {
    context.go('/home');
  }
}
