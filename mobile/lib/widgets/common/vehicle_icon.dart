import 'package:flutter/material.dart';

/// Icône correspondant au véhicule déclaré par le transporteur
/// (camion, pick-up, voiture).
IconData iconeVehicule(String? typeVehicule) {
  switch (typeVehicule) {
    case 'camion':
      return Icons.local_shipping;
    case 'pick-up':
      return Icons.airport_shuttle;
    case 'voiture':
      return Icons.directions_car;
    default:
      return Icons.directions_car_filled_outlined;
  }
}

/// Pastille ronde avec l'icône du véhicule, dans la couleur donnée.
class VehicleBadge extends StatelessWidget {
  final String? typeVehicule;
  final Color color;
  final double size;

  const VehicleBadge({super.key, required this.typeVehicule, required this.color, this.size = 48});

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(size / 4),
      ),
      child: Icon(iconeVehicule(typeVehicule), color: color, size: size / 2),
    );
  }
}
