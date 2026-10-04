"""Extraction d'images (frames) depuis la vidéo d'une demande.

Google Cloud Vision (et plus tard Groq) analysent des images, pas des vidéos :
on extrait quelques images réparties uniformément sur la durée de la vidéo,
redimensionnées et encodées en JPEG pour limiter la taille des requêtes.
"""

import cv2

TAILLE_MAX_PX = 1024
QUALITE_JPEG = 85


class VideoIllisible(Exception):
    """La vidéo envoyée par le client ne peut pas être décodée."""


def extraire_images(chemin_video: str, nombre: int) -> list[bytes]:
    """Retourne jusqu'à `nombre` images JPEG (bytes) extraites de la vidéo."""
    capture = cv2.VideoCapture(chemin_video)
    try:
        if not capture.isOpened():
            raise VideoIllisible("Impossible d'ouvrir la vidéo.")

        total = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if total > 0:
            # Positions réparties uniformément, en évitant le tout début et
            # la toute fin (souvent floues ou noires).
            positions = [
                int(total * (i + 1) / (nombre + 1)) for i in range(nombre)
            ]
        else:
            # Nombre d'images inconnu (certains conteneurs) : lecture
            # séquentielle des premières images.
            positions = [None] * nombre

        images = []
        for position in positions:
            if position is not None:
                capture.set(cv2.CAP_PROP_POS_FRAMES, position)
            ok, image = capture.read()
            if not ok or image is None:
                continue
            images.append(_encoder(image))
    finally:
        capture.release()

    if not images:
        raise VideoIllisible("Aucune image exploitable dans la vidéo.")
    return images


def _encoder(image) -> bytes:
    hauteur, largeur = image.shape[:2]
    ratio = TAILLE_MAX_PX / max(hauteur, largeur)
    if ratio < 1:
        image = cv2.resize(
            image,
            (int(largeur * ratio), int(hauteur * ratio)),
            interpolation=cv2.INTER_AREA,
        )
    ok, tampon = cv2.imencode(
        ".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), QUALITE_JPEG]
    )
    if not ok:
        raise VideoIllisible("Échec de l'encodage d'une image de la vidéo.")
    return tampon.tobytes()
