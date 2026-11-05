"""Score de confiance par sommet et par zone (phase 4).

Confiance = 1 - entropie normalisée des poids (0 = un seul os, 1 = poids uniformes sur tous les os).
Une valeur basse signale un sommet dont le résultat dépend d'un choix de poids ambigu.
Validation : les sommets repliés à une pose donnée doivent avoir une confiance plus basse que les autres.
"""
import numpy as np


def confiance(W):
    """Confiance par sommet, dans [0, 1]."""
    W = np.clip(W, 1e-12, None)
    W = W / W.sum(1, keepdims=True)
    H = -(W * np.log(W)).sum(1)
    Hmax = np.log(W.shape[1])
    return 1.0 - H / Hmax


def par_zone(conf, dominant_nom, zones):
    """Moyenne de confiance par zone ; zones : {zone: [os...]} (zone = os dominant du sommet)."""
    out = {}
    for z, os_list in zones.items():
        m = np.isin(dominant_nom, os_list)
        out[z] = {"n": int(m.sum()), "confiance_moyenne": float(conf[m].mean()) if m.any() else None}
    return out
