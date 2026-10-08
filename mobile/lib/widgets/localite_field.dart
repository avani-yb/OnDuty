import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../localization/app_localizations.dart';
import '../services/auth_service.dart';

/// Localités du Cameroun fournies par le serveur (chargées une seule fois).
final localitesProvider = FutureProvider<List<Localite>>((ref) async {
  final response = await ref.read(authServiceProvider).dio.get('/localites/');
  return (response.data as List)
      .map((e) => Localite(nom: e['nom'] as String, region: e['region'] as String))
      .toList();
});

class Localite {
  final String nom;
  final String region;

  const Localite({required this.nom, required this.region});
}

/// Minuscules sans accents : « Yaoundé » se trouve en tapant « yaounde ».
String _normaliser(String texte) {
  const avec = 'àâäáãåçéèêëíìîïñóòôöõúùûüýÿÀÂÄÁÃÅÇÉÈÊËÍÌÎÏÑÓÒÔÖÕÚÙÛÜÝ';
  const sans = 'aaaaaaceeeeiiiinooooouuuuyyAAAAAACEEEEIIIINOOOOOUUUUY';
  final buffer = StringBuffer();
  for (final c in texte.trim().toLowerCase().split('')) {
    final i = avec.indexOf(c);
    buffer.write(i >= 0 ? sans[i].toLowerCase() : c);
  }
  return buffer.toString();
}

/// Champ origine / destination : l'utilisateur tape « Ya », l'application
/// propose Yaoundé, Yagoua… et il doit choisir une localité de la liste
/// (le matching compare des noms identiques).
class LocaliteField extends ConsumerStatefulWidget {
  final TextEditingController controller;
  final String label;
  final bool enabled;

  const LocaliteField({super.key, required this.controller, required this.label, this.enabled = true});

  @override
  ConsumerState<LocaliteField> createState() => _LocaliteFieldState();
}

class _LocaliteFieldState extends ConsumerState<LocaliteField> {
  final _focus = FocusNode();

  @override
  void dispose() {
    _focus.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final l10n = AppLocalizations.of(context);
    final localites = ref.watch(localitesProvider).value ?? const <Localite>[];
    final noms = {for (final l in localites) _normaliser(l.nom): l.nom};

    return RawAutocomplete<Localite>(
      textEditingController: widget.controller,
      focusNode: _focus,
      displayStringForOption: (l) => l.nom,
      optionsBuilder: (saisie) {
        final texte = _normaliser(saisie.text);
        if (texte.isEmpty) return const Iterable<Localite>.empty();
        final debut = localites.where((l) => _normaliser(l.nom).startsWith(texte));
        final contient = localites.where((l) {
          final n = _normaliser(l.nom);
          return !n.startsWith(texte) && n.contains(texte);
        });
        return [...debut, ...contient].take(8);
      },
      fieldViewBuilder: (context, controller, focusNode, onSubmitted) => TextFormField(
        controller: controller,
        focusNode: focusNode,
        enabled: widget.enabled,
        decoration: InputDecoration(
          labelText: widget.label,
          hintText: l10n.cityHint,
          prefixIcon: const Icon(Icons.location_on_outlined),
          border: OutlineInputBorder(borderRadius: BorderRadius.circular(12)),
        ),
        validator: (v) {
          if (v == null || v.trim().isEmpty) return l10n.fillAllFields;
          // Liste pas encore chargée : le serveur validera.
          if (noms.isNotEmpty && !noms.containsKey(_normaliser(v))) return l10n.chooseCityFromList;
          return null;
        },
        // Saisie complète sans toucher la suggestion : on reprend le nom officiel.
        onChanged: (v) {
          final officiel = noms[_normaliser(v)];
          if (officiel != null && officiel != v && _normaliser(v).length >= officiel.length) {
            controller.value = TextEditingValue(
              text: officiel,
              selection: TextSelection.collapsed(offset: officiel.length),
            );
          }
        },
        onFieldSubmitted: (_) => onSubmitted(),
      ),
      optionsViewBuilder: (context, onSelected, options) => Align(
        alignment: Alignment.topLeft,
        child: Material(
          elevation: 4,
          borderRadius: BorderRadius.circular(12),
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxHeight: 260, maxWidth: 360),
            child: ListView(
              padding: EdgeInsets.zero,
              shrinkWrap: true,
              children: options
                  .map((l) => ListTile(
                        dense: true,
                        leading: const Icon(Icons.place_outlined),
                        title: Text(l.nom),
                        subtitle: Text(l.region),
                        onTap: () => onSelected(l),
                      ))
                  .toList(),
            ),
          ),
        ),
      ),
    );
  }
}
