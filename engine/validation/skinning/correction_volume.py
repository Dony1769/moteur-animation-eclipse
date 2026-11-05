"""Correction locale de volume (phase 4, étape B). Variante « normale » de Rohmer, Hahmann, Cani (CGF 2008, auteur :
imagine.inrialpes.fr/people/Damien.Rohmer, RHC_GTMG08.pdf, section 4).

Objectif : V(pos + u) = V_repos, avec u_i = rho_i * n_i (déplacement le long de la normale).
Linéarisation : sum_i <grad V_i, n_i> rho_i = D, D = V_repos - V(pos).
Solution (Rohmer, eq. 11, signe corrigé ici) : rho_i = D * gamma_i <n_i, g_i> / sum_k gamma_k <n_k, g_k>^2.
Localité : gamma_i = (1 - max_j w_ij)^G (poids normalisés). Nul sur un os pur, grand dans les zones de transition.
G = 1 fixé avant toute mesure, identique pour tous les personnages.
Multi-étapes : M itérations, chacune recalcule D (suggestion de l'article, non testée par eux).

Gradient : V = sum_triangles a.(b x c)/6 ; dV/da = (b x c)/6, dV/db = (c x a)/6, dV/dc = (a x b)/6 (fan, identique aux mesures).
"""
import numpy as np

G_LOCAL = 1.0  # fixé avant mesure


def _triangles(boucle, tot):
    debut = np.concatenate([[0], np.cumsum(tot)[:-1]]).astype(np.int64)
    T = []
    for p in range(len(tot)):
        vs = boucle[debut[p]:debut[p] + tot[p]]
        for k in range(1, len(vs) - 1):
            T.append((vs[0], vs[k], vs[k + 1]))
    return np.array(T, dtype=np.int64)


def volume_et_gradient(p, T):
    a, b, c = p[T[:, 0]], p[T[:, 1]], p[T[:, 2]]
    V = float(np.einsum("ij,ij->i", a, np.cross(b, c)).sum() / 6.0)
    g = np.zeros_like(p)
    np.add.at(g, T[:, 0], np.cross(b, c) / 6.0)
    np.add.at(g, T[:, 1], np.cross(c, a) / 6.0)
    np.add.at(g, T[:, 2], np.cross(a, b) / 6.0)
    return V, g


def normales_sommets(p, boucle, tot):
    debut = np.concatenate([[0], np.cumsum(tot)[:-1]]).astype(np.int64)
    poly = np.repeat(np.arange(len(tot)), tot)
    local = np.arange(len(boucle)) - debut[poly]
    nxt = debut[poly] + (local + 1) % tot[poly]
    cr = np.cross(p[boucle], p[boucle[nxt]])
    newell = np.add.reduceat(cr, debut, axis=0)  # par polygone
    n = np.zeros_like(p)
    np.add.at(n, boucle, newell[poly])
    nn = np.linalg.norm(n, axis=1, keepdims=True)
    return n / np.maximum(nn, 1e-18)


def gamma_locale(Wi, Ww, G=G_LOCAL):
    valide = Wi >= 0
    w = np.where(valide, Ww, 0.0)
    s = w.sum(axis=1, keepdims=True)
    wn = np.where(s > 1e-12, w / np.maximum(s, 1e-12), 0.0)
    return np.clip(1.0 - wn.max(axis=1), 0.0, 1.0) ** G


def corriger(pos, rest, Wi, Ww, boucle, tot, T=None, M=1, G=G_LOCAL):
    """Retourne (pos corrigé, diagnostic). M = nombre d'étapes."""
    if T is None:
        T = _triangles(boucle, tot)
    V_rest, _ = volume_et_gradient(rest, T)
    gam = gamma_locale(Wi, Ww, G)
    p = pos.copy()
    diag = {"volume_repos": V_rest, "delta_V_avant": None, "etapes": []}
    for m in range(M):
        V, grad = volume_et_gradient(p, T)
        D = V_rest - V
        if m == 0:
            diag["delta_V_avant"] = D
        n = normales_sommets(p, boucle, tot)
        gn = np.einsum("ij,ij->i", n, grad)
        denom = float(np.sum(gam * gn * gn))
        if denom < 1e-18:
            diag["etapes"].append({"arret": "denominateur nul"})
            break
        rho = D * gam * gn / denom
        p = p + rho[:, None] * n
        V2, _ = volume_et_gradient(p, T)
        diag["etapes"].append({"delta_V_apres": V_rest - V2})
    diag["delta_V_apres"] = V_rest - volume_et_gradient(p, T)[0]
    diag["relatif_avant"] = diag["delta_V_avant"] / V_rest
    diag["relatif_apres"] = diag["delta_V_apres"] / V_rest
    return p, diag
