"""Vues multiples : choix et fondu entre des rendus de face, trois quarts, profil.

Pseudo-rotation 3D sans modèle 3D : pour un angle de caméra (0 = face, 45 = trois quarts,
90 = profil), on prend les deux vues réelles encadrant l'angle et on les mélange linéairement.
C'est un fondu enchaîné entre deux images, pas une rotation : les vues ne sont pas recalées
entre elles, donc un fondu à mi-chemin montre un doublement des contours.

Une vue absente (ex. profil) n'est jamais inventée : au-delà de la dernière vue réelle, on
répète cette dernière et le drapeau `hors_plage` le signale.
"""
import numpy as np


def poids_vues(angle, angles_vues):
    """Liste [(nom_vue, poids)] (poids > 0, somme 1) et drapeau `hors_plage`.

    angles_vues : {angle_deg: nom_vue}, au moins une entrée, angles distincts.
    Entre deux angles réels : fondu linéaire. Hors de la plage : vue la plus proche, sans fondu.
    hors_plage vaut True seulement si angle est au-delà de la dernière vue réelle (ex. profil
    demandé alors que seules face et trois quarts existent).
    """
    if not angles_vues:
        raise ValueError("aucune vue disponible")
    angles = sorted(float(a) for a in angles_vues)
    nom = {float(a): n for a, n in angles_vues.items()}
    a = float(angle)
    if not np.isfinite(a):
        raise ValueError("angle non fini")
    if a <= angles[0]:
        return [(nom[angles[0]], 1.0)], False
    if a >= angles[-1]:
        return [(nom[angles[-1]], 1.0)], a > angles[-1]
    for a0, a1 in zip(angles, angles[1:]):
        if a0 <= a <= a1:
            s = (a - a0) / (a1 - a0)
            poids = [(nom[a0], 1.0 - s), (nom[a1], s)]
            return [(n, w) for n, w in poids if w > 1e-12], False
    raise AssertionError("angle hors des bornes non détecté")  # pragma: no cover


def fondre(images, poids):
    """Mélange pondéré d'images de même forme. images : {nom: (H, W, C)} ; poids : [(nom, w)]."""
    if not poids:
        raise ValueError("aucun poids")
    somme = sum(w for _, w in poids)
    if abs(somme - 1.0) > 1e-9:
        raise ValueError(f"poids non normalisés (somme {somme})")
    forme = None
    sortie = None
    for n, w in poids:
        im = np.asarray(images[n], np.float32)
        if forme is None:
            forme = im.shape
            sortie = np.zeros(forme, np.float32)
        elif im.shape != forme:
            raise ValueError("images de tailles différentes")
        sortie += float(w) * im
    return sortie


def bascule(images, poids):
    """Sprite le plus proche, sans fondu : la vue de poids maximal (ex. style animé à vues figées)."""
    nom = max(poids, key=lambda p: p[1])[0]
    return np.asarray(images[nom], np.float32).copy()
