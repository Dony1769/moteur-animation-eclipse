"""Vues multiples : bascule de sprites au seuil d'angle, et fondu (ancien mode, à éviter).

Pseudo-rotation 3D sans modèle 3D : pour un angle de caméra (0 = face, 45 = trois quarts,
90 = profil), le mode retenu est la bascule nette (`vue_nette`) : on affiche la vue réelle la
plus proche, et on change de vue au point médian. Une transition FFD courte (`appliquer_transition`)
accompagne le changement, pour qu'il ne soit pas un saut sec.

Le fondu (`poids_vues` + `fondre`) mélange deux images : les vues ne sont pas recalées, donc un
fondu à mi-chemin dessine deux personnages superposés. Il est conservé pour les comparaisons.

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


def vue_nette(angle, angles_vues):
    """Bascule nette : (nom de la vue réelle la plus proche, hors_plage).

    Le changement a lieu au point médian entre deux angles réels consécutifs (pas de fondu).
    hors_plage vaut True au-delà de la dernière vue réelle.
    """
    if not angles_vues:
        raise ValueError("aucune vue disponible")
    angles = sorted(float(a) for a in angles_vues)
    nom = {float(a): n for a, n in angles_vues.items()}
    a = float(angle)
    if not np.isfinite(a):
        raise ValueError("angle non fini")
    proche = min(angles, key=lambda c: abs(c - a)) if a <= angles[-1] else angles[-1]
    # Intervalle [a0, a1[ : à l'angle médian exact, la vue suivante (a1) prend le relais.
    for a0, a1 in zip(angles, angles[1:]):
        if a0 <= a < a1:
            proche = a0 if a < 0.5 * (a0 + a1) else a1
            break
    return nom[proche], a > angles[-1]


def decalage_transition(s, amplitude):
    """Amplitude (pixels) de la transition FFD à la phase s ∈ [0, 1] : nulle aux bornes, maximale à 0,5."""
    if not 0.0 <= s <= 1.0:
        raise ValueError("phase hors de [0, 1]")
    return float(amplitude) * float(np.sin(np.pi * s))


def appliquer_transition(grilles, s, amplitude):
    """Cisaillement FFD léger, écrit dans chaque grille (GrilleFFD) : déplacement horizontal croissant vers le bas.

    Le champ vaut dx = A(s) · (y − y_milieu) / (demi-hauteur) sur les points de contrôle : au sommet
    la tête ne bouge pas, au menton elle se décale de A(s). Nul pour s = 0 et s = 1.
    """
    A = decalage_transition(s, amplitude)
    for g in grilles:
        x0, y0, x1, y1 = g.boite
        milieu = 0.5 * (y0 + y1)
        demi = 0.5 * (y1 - y0)
        dec = np.zeros((g.ny, g.nx, 2))
        dec[..., 0] = A * (g.repos[..., 1] - milieu) / demi
        g.decalages = dec
    return A
