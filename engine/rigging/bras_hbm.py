"""Bras, avant-bras et mains pour le corps HBM sans armature (phase 3).

Méthode :
 1. chemin MESURÉ du bras : centroïdes des sommets par tranche de hauteur (0,84 h -> 0,45 h), côté
    considéré, en excluant le tronc (|x| > 0,20 m) ;
 2. longueur d'arc sur ce chemin ; coude et poignet placés à des longueurs anatomiques (fractions de la
    hauteur totale : humérus 0,186 h, avant-bras 0,146 h, main 0,108 h) ; c'est une ESTIMATION, signalée
    comme telle dans le rapport ;
 3. les validations (symétrie, dans le maillage, longueurs plausibles) sont dans engine/validation.

Fonctions pures (sans Blender) : chemin_bras, placer_articulations.
"""
import math

FRACTIONS = {"humerus": 0.186, "avant_bras": 0.146, "main": 0.108}


def chemin_bras(points, cote, zmin, h, cote_min_x=0.20):
    """Chemin mesuré du bras : liste de (z_frac, x, y, z) de haut en bas.

    points : sommets (x, y, z) déjà recentrés en X ; cote = +1 (gauche) ou -1 (droite).
    """
    chemin = []
    for k in range(40):
        f = 0.84 - 0.01 * k
        z0, z1 = zmin + (f - 0.006) * h, zmin + (f + 0.006) * h
        sel = [p for p in points if z0 <= p[2] <= z1 and cote * p[0] >= cote_min_x and cote * p[0] <= 0.60]
        if len(sel) >= 3:
            n = len(sel)
            x = sum(p[0] for p in sel) / n
            y = sum(p[1] for p in sel) / n
            chemin.append((round(f, 3), x, y, zmin + f * h))
    return chemin


def _longueurs(chemin):
    s = [0.0]
    for a, b in zip(chemin[:-1], chemin[1:]):
        d = math.dist((a[1], a[2], a[3]), (b[1], b[2], b[3]))
        s.append(s[-1] + d)
    return s


def _point_a(chemin, s, cible):
    """Point du chemin à la longueur d'arc cible.

    Retourne (point, extrapole). Si la cible dépasse la fin du chemin mesuré, le point est prolongé
    linéairement dans la direction du dernier segment et marqué extrapole=True (jamais présenté comme mesuré).
    """
    if cible <= s[-1]:
        for i in range(len(s) - 1):
            if s[i] <= cible <= s[i + 1]:
                t = 0.0 if s[i + 1] == s[i] else (cible - s[i]) / (s[i + 1] - s[i])
                a, b = chemin[i], chemin[i + 1]
                return (a[1] + t * (b[1] - a[1]), a[2] + t * (b[2] - a[2]), a[3] + t * (b[3] - a[3])), False
        return None, False
    a, b = chemin[-2], chemin[-1]
    d = math.dist((a[1], a[2], a[3]), (b[1], b[2], b[3]))
    t = (cible - s[-1]) / d if d > 0 else 0.0
    return (b[1] + t * (b[1] - a[1]), b[2] + t * (b[2] - a[2]), b[3] + t * (b[3] - a[3])), True


def placer_articulations(chemin, h):
    """Épaule, coude, poignet, bout de la main, à partir du chemin mesuré et des fractions anatomiques.

    Retourne {nom: (x, y, z)} et {nom: extrapole}. Une articulation impossible à placer est None.
    """
    if len(chemin) < 3:
        return None, None
    s = _longueurs(chemin)
    l_hum = FRACTIONS["humerus"] * h
    l_fa = FRACTIONS["avant_bras"] * h
    l_main = FRACTIONS["main"] * h
    epaule = (chemin[0][1], chemin[0][2], chemin[0][3])
    coude, e1 = _point_a(chemin, s, l_hum)
    poignet, e2 = _point_a(chemin, s, l_hum + l_fa)
    bout, e3 = _point_a(chemin, s, l_hum + l_fa + l_main)
    pts = {"epaule": epaule, "coude": coude, "poignet": poignet, "bout_main": bout}
    extra = {"epaule": False, "coude": e1, "poignet": e2, "bout_main": e3}
    return pts, extra
