"""Règle de tolérance des plis, par zone anatomique (phase 4).

Un pli n'est acceptable que s'il est un vrai pli de peau :
  - dans une zone de pli anatomique : pli de l'aine (inguinal), pli fessier inférieur, creux poplité
    (arrière du genou), pli du coude (face interne), creux axillaire ;
  - sans pénétration : le pli ne traverse aucune autre surface (à vérifier visuellement) ;
  - hors de ces zones : aucun pli n'est accepté (le trochanter et le fessier externe ne plissent pas).
Les plis hors zone sont des défauts à corriger.
"""
import numpy as np

ZONES_ACCEPTABLES = {
    "aine": {"centre_rel_hanche": (0.0, 0.0, -0.02), "rayon": 0.13},  # sous le centre de la hanche, face interne
    # à compléter pour genou (creux poplité), coude (pli interne), aisselle
}


def classer(plis_centres, hanche):
    """plis_centres : (n,3) centres des faces repliées ; hanche : centre de la hanche.
    Retourne (acceptes, defauts) : listes d'indices."""
    acceptes, defauts = [], []
    z = ZONES_ACCEPTABLES["aine"]
    centre = np.array(hanche) + np.array(z["centre_rel_hanche"])
    for i, c in enumerate(plis_centres):
        (acceptes if np.linalg.norm(c - centre) < z["rayon"] else defauts).append(i)
    return acceptes, defauts
