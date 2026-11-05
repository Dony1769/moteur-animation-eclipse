"""Limites anatomiques par articulation (phase 4, erreur 87).

Convention : angle positif = flexion (ou dorsiflexion pour la cheville), négatif = extension
(ou flexion plantaire pour la cheville). Une pose hors de ces bornes n'est pas une pose humaine.

Source des bornes : CDC / NCHS, « Public Use Dataset for Normal Joint Range of Motion » (674 sujets sans
pathologie), moyennes et valeurs extrêmes. Les bornes retenues sont les moyennes arrondies, sauf
l'hyperextension, prise à la moyenne (les valeurs extrêmes, 19 à 22°, sont individuelles).
Mouvements absents de cette source (abduction de la hanche, abduction et élévation de l'épaule,
poignet) : bornes marquées « non vérifié », à remplacer par une source officielle.
"""

LIMITES = {
    "genou":    {"type": "charniere", "min": -5,  "max": 140, "source": "CDC flexion 140,1 ; hyperextension moyenne 1,9"},
    "coude":    {"type": "charniere", "min": -4,  "max": 148, "source": "CDC flexion 148,0 ; hyperextension moyenne 3,9"},
    "cheville": {"type": "charniere", "min": -56, "max": 15,  "source": "CDC flexion plantaire 56,7 ; dorsiflexion 14,8"},
    "hanche":   {"type": "rotule",    "min": -20, "max": 130, "source": "CDC flexion 132 ; extension moyenne 18,6 (sens négatif)"},
    "epaule":   {"type": "rotule",    "min": -60, "max": 170, "source": "CDC flexion 170,4 ; extension non vérifiée (bornée)"},
    "poignet":  {"type": "condylienne", "min": -10, "max": 80, "source": "NON VÉRIFIÉ (absent du jeu CDC) : bornes à remplacer"},
}


def dans_limites(articulation, angle):
    """True si l'angle (degrés) est dans les bornes anatomiques de l'articulation."""
    L = LIMITES[articulation]
    return L["min"] <= angle <= L["max"]


def hors_limites(articulation, angles):
    """Liste des angles hors bornes (pour refuser une pose ou la signaler)."""
    return [a for a in angles if not dans_limites(articulation, a)]
