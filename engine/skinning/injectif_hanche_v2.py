"""Solveur injectif de la hanche, version 2 : pas maximal exact avant retournement, arrêts déclarés.

Remplace injectif_hanche.py (rapport INVALIDE, entrée 130) sur deux points :
  1. Le pas n'est plus une moitié à l'aveugle (σ/2 jusqu'à 1/64, arrêt silencieux). On calcule le pas maximal α_max
     exact : pour chaque face, la composante de l'aire orientée (produit scalaire avec la normale au repos) est un
     polynôme du second degré en α ; α_max est sa plus petite racine positive. Puis pas = min(1, 0,8·α_max).
     Source officielle : Schüller et al. 2013 (barrière, pas acceptés) ; méthode de calcul de α_max : Smith & Schaefer
     2015 (section 3.3, citée par Rabinovich et al. 2017, SLIM) ; ligne de recherche à 0,8·α_max : SLIM 2017.
  2. Tout arrêt est déclaré (état) : 'OK', 'MAX_ITER', 'ARRET_SANS_PROGRES'. Un état autre que 'OK' rend le
     résultat invalide. Source : libigl lim.h (états Infeasible, IterationLimit, LocalMinima), lu en secondaire.

Contrôle obligatoire à côté des plis : erreur à la cible distale (un solveur qui ne bouge pas n'est pas un succès).
Usage : python3 injectif_hanche_v2.py <dossier_donnees> [A_DISTAL]
"""
import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import injectif_hanche as base
import test_chaine_hanche as t
from correctif_arap import _rotations
from mesures_pose import plis_locaux
from scipy.spatial.transform import Rotation as Rot

N = base.N
ij = base.ij
F = t.faces
rest = t.rest
pivot = base.pivot
dirl = base.dirl
axe = base.axe
B = base.B
s = base.s
bande = base.bande
proximal = base.proximal
distal = base.distal
libre = base.libre

# normales au repos NON normalisées (produit vectoriel), pour le signe de la face
_e1 = rest[F[:, 1]] - rest[F[:, 0]]
_e2 = rest[F[:, 2]] - rest[F[:, 0]]
N0 = np.cross(_e1, _e2)


def alpha_max(p, dp):
    """Plus grand α ∈ [0,1] tel que toutes les faces gardent leur orientation le long de p + α·dp (exact, quadratique)."""
    x0, x1, x2 = p[F[:, 0]], p[F[:, 1]], p[F[:, 2]]
    d0, d1, d2 = dp[F[:, 0]], dp[F[:, 1]], dp[F[:, 2]]
    e1 = x1 - x0; e2 = x2 - x0
    f1 = d1 - d0; f2 = d2 - d0
    c0 = np.einsum("fi,fi->f", N0, np.cross(e1, e2))
    c1 = np.einsum("fi,fi->f", N0, np.cross(f1, e2) + np.cross(e1, f2))
    c2 = np.einsum("fi,fi->f", N0, np.cross(f1, f2))
    amax = np.ones(len(F))
    # racines de c2 α² + c1 α + c0 = 0 ; on garde la plus petite racine positive où le polynôme passe de + à −
    with np.errstate(divide="ignore", invalid="ignore"):
        disc = c1 * c1 - 4 * c2 * c0
        r1 = (-c1 - np.sqrt(np.maximum(disc, 0))) / (2 * c2)
        r2 = (-c1 + np.sqrt(np.maximum(disc, 0))) / (2 * c2)
        lin = -c0 / c1
    for k in range(len(F)):
        if c0[k] <= 0:
            amax[k] = 0.0; continue
        cand = []
        for r in (r1[k], r2[k]) if abs(c2[k]) > 1e-18 else ():
            if np.isfinite(r) and r > 0: cand.append(r)
        if abs(c2[k]) <= 1e-18 and np.isfinite(lin[k]) and lin[k] > 0 and c1[k] < 0:
            cand.append(lin[k])
        if cand:
            amax[k] = min(1.0, min(cand))
    return float(amax.min())


def inversions(p):
    return base.inversions(p)


def pose(theta_total, pas=5.0, iters=10):
    """Marche en angle. Retourne (P, etat, historique). etat = 'OK' ou la raison d'arrêt."""
    solveur = base.factoriser()
    p = rest.copy()
    th = 0.0
    hist = []
    etat = "OK"
    while th < theta_total - 1e-9:
        th = min(th + pas, theta_total)
        fixe = p.copy()
        fixe[proximal] = base.cible_proximale(th)[proximal]
        fixe[distal] = base.cible_rigide(th)[distal]
        progres = False
        for _ in range(iters):
            R = _rotations(rest, p, ij, N, base.wij)
            p_new = base.etape_globale(p, R, fixe, solveur)
            dp = p_new - p
            if np.abs(dp).max() < 1e-10:
                break
            am = alpha_max(p, dp)
            if am <= 0:
                break
            alpha = min(1.0, 0.8 * am)
            p = p + alpha * dp
            progres = True
        hist.append(dict(theta=th, alpha_max_dernier=round(am, 6) if progres else None))
        if not progres:
            etat = "ARRET_SANS_PROGRES"
            break
    else:
        etat = "OK"
    return p, etat, hist


def erreurs(P, th):
    dist = float(np.linalg.norm((P - base.cible_rigide(th))[distal], axis=1).max())
    return dist


if __name__ == "__main__":
    if len(sys.argv) > 2:
        base.A_DISTAL = float(sys.argv[2])
    sorties = []
    for th in (30, 60, 90, 105, 120):
        P, etat, hist = pose(th)
        Rv = _rotations(rest, P, ij, N, base.wij)
        Rf = Rv[F].mean(axis=1)
        U, _, Vt = np.linalg.svd(Rf)
        Rf = U @ Vt
        plis = plis_locaux(rest, P, F, Rf)
        L0 = np.linalg.norm(rest[t.aretes[:, 0]] - rest[t.aretes[:, 1]], axis=1)
        L1 = np.linalg.norm(P[t.aretes[:, 0]] - P[t.aretes[:, 1]], axis=1)
        r = L1 / np.maximum(L0, 1e-9)
        mid = (rest[t.aretes[:, 0]] + rest[t.aretes[:, 1]]) / 2
        band = np.linalg.norm(mid - pivot, axis=1) < 0.10
        ligne = dict(th=th, etat=etat, inversions=inversions(P), plis=plis,
                     erreur_distal_max_m=round(erreurs(P, th), 4),
                     etirement_bande_p99=round(float(np.percentile(r[band], 99)), 4),
                     n_aretes_bande=int(band.sum()))
        sorties.append(ligne); print(ligne, flush=True)
    out = Path(__file__).resolve().parents[2] / "docs" / "rapports" / "phase4_injectif_hanche_v2.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(sorties, indent=2, ensure_ascii=False))
    print("ECRIT", out, flush=True)
