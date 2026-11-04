"""Optimisation des poids de skinning contre les déformations d'arêtes (inspirée d'ARAP-LBS, Thiery et al.).

Objectif, sur des poses d'entraînement a ∈ TRAIN :
   E(W) = Σ_a Σ_arêtes (|x'_i - x'_j| / L_ij - 1)²  +  λ · Σ (W - W0)²
Contraintes : W_ib ≥ 0, Σ_b W_ib = 1 par sommet, support inchangé (mêmes os qu'au départ).
Descente de gradient projetée sur le simplexe, pas adaptatif (retour arrière si la perte augmente).
Évaluation honnête : TEST (poses jamais vues à l'entraînement) et TEMOIN (0°, doit rester identique).
"""
import numpy as np
from lbs_numpy import deformer, etirements


def projeter_simplexe(V, S):
    """Projection de chaque ligne de V sur le simplexe, en ne gardant que le support S (booléen)."""
    out = np.zeros_like(V)
    for i in range(V.shape[0]):
        s = S[i]
        if not s.any(): continue
        v = V[i, s]
        u = np.sort(v)[::-1]
        css = np.cumsum(u)
        rho = np.nonzero(u * np.arange(1, len(u) + 1) > (css - 1))[0][-1]
        theta = (css[rho] - 1) / (rho + 1.0)
        out[i, s] = np.maximum(v - theta, 0)
    return out


def perte_et_grad(W, rest, aretes, Ms, L, W0, lam, puissance=2):
    perte = 0.0
    gW = np.zeros_like(W)
    for M in Ms:
        R = M[:, :3, :3]; t = M[:, :3, 3]
        Y = np.einsum("bij,nj->nbi", R, rest) + t[None]          # (N,B,3)
        x = np.einsum("nb,nbi->ni", W, Y)                         # (N,3)
        d = x[aretes[:, 0]] - x[aretes[:, 1]]
        nd = np.linalg.norm(d, axis=1) + 1e-12
        rho = nd / L
        e = rho - 1.0
        # puissance 2 : écart quadratique (défaut) ; puissance 4 : pénalise davantage les arêtes extrêmes
        perte += np.sum(np.abs(e) ** puissance)
        # dE/dx_i via arêtes : p |e|^(p-2) e (d/|d|)/L  (p=2 : 2e(d/|d|)/L)
        g_arete = (puissance * np.abs(e) ** (puissance - 2) * e / (nd * L))[:, None] * d
        gx = np.zeros_like(x)
        np.add.at(gx, aretes[:, 0], g_arete)
        np.add.at(gx, aretes[:, 1], -g_arete)
        gW += np.einsum("ni,nbi->nb", gx, Y)
    perte += lam * np.sum((W - W0) ** 2)
    gW += 2 * lam * (W - W0)
    return perte, gW


def optimiser(data, ia_train, lam=1e-3, pas=0.2, iters=400, W0=None, puissance=2):
    rest, aretes = data["rest"], data["aretes"]
    W0 = data["W"] if W0 is None else W0
    S = W0 > 0
    L = np.linalg.norm(rest[aretes[:, 0]] - rest[aretes[:, 1]], axis=1)
    ok = L > 0
    aretes, L = aretes[ok], L[ok]
    Ms = [data["M"][i] for i in ia_train]
    W = W0.copy(); h = pas
    p, g = perte_et_grad(W, rest, aretes, Ms, L, W0, lam, puissance)
    historique = [p]
    for it in range(iters):
        Wn = projeter_simplexe(W - h * g, S)
        pn, gn = perte_et_grad(Wn, rest, aretes, Ms, L, W0, lam, puissance)
        if pn <= p:
            W, p, g = Wn, pn, gn; h *= 1.05
        else:
            h *= 0.5
        historique.append(p)
    return W, historique


def evaluer(data, W, ia):
    pts = deformer(data["rest"], W, data["M"][ia])
    return etirements(pts, data["rest"], data["aretes"])
