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


def classer_hanche(plis_centres, pivot_hanche, rayon=0.15):
    """Règle qualitative (phase 4, erreur 117) : un pli de hanche n'est acceptable que côté fléchisseur antérieur
    (Y > 0 dans le repère HBM, direction des orteils) et à moins de `rayon` du centre de la hanche.
    Les coordonnées exactes du pli de l'aine ne sont PAS sourcées (Wikipedia, Medscape, Larkin 2014 : pas de chiffre).
    Retourne (acceptes, defauts)."""
    acceptes, defauts = [], []
    for i, c in enumerate(plis_centres):
        rel = np.asarray(c) - np.asarray(pivot_hanche)
        ok = rel[1] > 0 and np.linalg.norm(rel) < rayon
        (acceptes if ok else defauts).append(i)
    return acceptes, defauts
