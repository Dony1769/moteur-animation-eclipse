"""Poids par distance aux os (base du skinning automatique, phase 4).

Pour chaque sommet de repos : distance au segment de chaque os (tête -> queue, repère armature),
poids = 1 / d^p sur les K os les plus proches, normalisé à 1. Déterministe, sans optimisation.
Les poids optimisés (W_seq_final) restent la référence ; cette version sert de base et de témoin.
"""
import numpy as np


def distance_segment(P, a, b):
    """Distance de chaque point de P au segment [a, b]."""
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-12), 0.0, 1.0)
    proj = a + np.outer(t, ab)
    return np.linalg.norm(P - proj, axis=1)


def poids_distance(rest, os_nom, os_repos, K=4, p=2.0, eps=1e-4):
    """Matrice (N, B) des poids par distance ; os_repos : {nom: {tete, queue}}."""
    N, B = len(rest), len(os_nom)
    D = np.zeros((N, B))
    for ib, nom in enumerate(os_nom):
        a = np.array(os_repos[nom]["tete"]); b = np.array(os_repos[nom]["queue"])
        D[:, ib] = distance_segment(rest, a, b)
    W = np.zeros((N, B))
    idx = np.argsort(D, axis=1)[:, :K]
    rows = np.arange(N)[:, None]
    W[rows, idx] = 1.0 / (D[rows, idx] ** p + eps)
    W /= W.sum(1, keepdims=True)
    return W
