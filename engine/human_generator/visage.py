"""Construction du visage par régions (phase 3), à partir des cibles CC0 de MakeHuman (dossier targets/).

Chaque région (nez, menton, pommettes, front, oreilles, bouche, yeux, sourcils) a ses propres cibles de forme. Une cible
ne doit déplacer que les sommets de SA région : c'est le critère de localité testé dans test_visage.py.

Une cible valide contient au moins une ligne de données « index dx dy dz ». Les fichiers qui n'en contiennent aucune
(8 sur 1 280 dans le dépôt, dont les universal-*) sont écartés et signalés, jamais appliqués (entrée 136).
"""
from pathlib import Path
import numpy as np
import corps as c

REGIONS = ("nose", "chin", "cheek", "forehead", "ears", "mouth", "eyes", "eyebrows")


def contient_donnees(chemin_fichier):
    """Vrai si le fichier .target contient au moins une ligne de déplacement (index dx dy dz)."""
    with open(chemin_fichier) as f:
        for ligne in f:
            p = ligne.split()
            if len(p) == 4 and not ligne.startswith("#"):
                return True
    return False


def cibles_region(region):
    """Liste (chemin_relatif, est_valide) des cibles d'une région. Une cible sans ligne de données est marquée invalide."""
    dossier = c.DATA / "targets" / region
    out = []
    for p in sorted(dossier.glob("*.target")):
        valide = contient_donnees(p)
        out.append((f"{region}/{p.name}", valide))
    return out


def appliquer_region(V, chemin, poids):
    """Applique une cible si elle est valide ; lève une erreur sur un pointeur LFS (jamais de silence)."""
    p = c.DATA / "targets" / chemin
    if not contient_donnees(p):
        raise ValueError(f"cible vide, aucune donnée de déplacement : {chemin}")
    return c.appliquer_cible(V, chemin, poids)


def sommets_de_region(V0, region, cibles_valides):
    """Indices des sommets qui bougent avec les cibles valides de la région (ensemble d'appartenance)."""
    bouge = np.zeros(len(V0), dtype=bool)
    for chemin in cibles_valides:
        idx, _ = c.charger_cible(chemin)
        bouge[idx] = True
    return bouge
