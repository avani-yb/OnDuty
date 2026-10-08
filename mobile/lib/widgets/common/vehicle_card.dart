import 'package:flutter/material.dart';

import 'vehicle_icon.dart';

/// Image détourée du véhicule (camion, pick-up, voiture). Si l'image n'est
/// pas disponible, l'icône Material du type de véhicule est affichée.
class VehiculeImage extends StatelessWidget {
  final String? typeVehicule;
  final double largeur;
  final double hauteur;
  final Color couleurSecours;

  const VehiculeImage({
    super.key,
    required this.typeVehicule,
    this.largeur = 96,
    this.hauteur = 64,
    this.couleurSecours = Colors.grey,
  });

  static String _asset(String? type) {
    switch (type) {
      case 'camion':
        return 'assets/images/vehicule_camion.png';
      case 'pick-up':
        return 'assets/images/vehicule_pickup.png';
      default:
        return 'assets/images/vehicule_voiture.png';
    }
  }

  @override
  Widget build(BuildContext context) {
    return SizedBox(
      width: largeur,
      height: hauteur,
      child: Image.asset(
        _asset(typeVehicule),
        fit: BoxFit.contain,
        errorBuilder: (context, erreur, pile) => Icon(iconeVehicule(typeVehicule), color: couleurSecours, size: hauteur * 0.7),
      ),
    );
  }
}

/// Carte de liste dont l'image du véhicule déborde légèrement en haut à
/// gauche, comme si le véhicule allait toucher le texte.
class CarteVehicule extends StatelessWidget {
  final String? typeVehicule;
  final Color couleur;
  final String titre;
  final String sousTitre;
  final Widget? trailing;
  final VoidCallback? onTap;

  const CarteVehicule({
    super.key,
    required this.typeVehicule,
    required this.couleur,
    required this.titre,
    required this.sousTitre,
    this.trailing,
    this.onTap,
  });

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 14),
      child: Stack(
        clipBehavior: Clip.none,
        children: [
          Card(
            margin: const EdgeInsets.only(left: 8, top: 12),
            shape: RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(16),
              side: BorderSide(color: couleur.withValues(alpha: 0.45)),
            ),
            child: InkWell(
              onTap: onTap,
              borderRadius: BorderRadius.circular(16),
              child: Padding(
                padding: const EdgeInsets.fromLTRB(92, 16, 12, 16),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(titre, style: const TextStyle(fontWeight: FontWeight.w600)),
                          const SizedBox(height: 4),
                          Text(sousTitre, style: Theme.of(context).textTheme.bodySmall),
                        ],
                      ),
                    ),
                    if (trailing != null) ...[const SizedBox(width: 8), trailing!],
                  ],
                ),
              ),
            ),
          ),
          // Déborde de la carte (en haut et à gauche).
          Positioned(
            left: -2,
            top: -2,
            child: IgnorePointer(
              child: VehiculeImage(typeVehicule: typeVehicule, couleurSecours: couleur),
            ),
          ),
        ],
      ),
    );
  }
}

/// Pastille de statut colorée, utilisée à droite des cartes.
class PastilleStatut extends StatelessWidget {
  final String texte;
  final Color couleur;

  const PastilleStatut({super.key, required this.texte, required this.couleur});

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
      decoration: BoxDecoration(
        color: couleur.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(20),
      ),
      child: Text(texte, style: TextStyle(color: couleur, fontWeight: FontWeight.w600, fontSize: 11)),
    );
  }
}
