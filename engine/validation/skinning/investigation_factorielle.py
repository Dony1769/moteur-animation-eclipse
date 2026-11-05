"""Plan factoriel 2 × 2 × 2 sur géométries synthétiques contrôlées (la correspondance réelle masculin / féminin est
invalide : erreur médiane 2 cm, non injective ; voir RAPPORT_factorielle.md).

Facteurs :
  G (géométrie) : espacement des arêtes, mesuré sur l'entrejambe natif : M = 0,0300 m ; F = 0,0285 m.
  W (poids)     : distribution des poids G des sommets mixtes, histogramme natif (10 classes) ; appliquée par
                  quantiles sur une bande de transition (|x| ≤ 0,10 m), triée selon x. M ou F.
  T (triangulation) : A = diagonales toutes parallèles ; B = diagonales alternées (même géométrie, mêmes sommets).

Mouvement : os G tourne de 120° autour de l'axe y (origine) ; os D fixe. Somme des poids = 1. LBS et SQ
(moyenne arithmétique, configuration actuelle, λ = 0,1) utilisent exactement les mêmes données.

Mesures : maximum et p99 des étirements (globaux et dans la bande), retournements (repère rigide local),
compression minimale des triangles, et leurs écarts SQ − LBS.
Effets principaux et interactions par contrastes (moyennes sur les 8 cellules).
"""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "factorielle")


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


S = charger("investigation_synthetique")
DEC = S.DEC
ARAP = S.ARAP
LAM = 0.1
ESP = {"M": 0.0300, "F": 0.0285}
BANDE = 0.10
L_DOM = 0.60


def grille_T(xs, ys, mode):
    nx, ny = len(xs), len(ys)
    X, Y = np.meshgrid(xs, ys)
    rest = np.column_stack([X.ravel(), Y.ravel(), np.zeros(nx * ny)])
    idx = np.arange(nx * ny).reshape(ny, nx)
    tris = []
    for j in range(ny - 1):
        for i in range(nx - 1):
            p00, p10, p01, p11 = idx[j, i], idx[j, i + 1], idx[j + 1, i], idx[j + 1, i + 1]
            diag_alt = (mode == "B") and ((i + j) % 2 == 1)
            if not diag_alt:
                tris += [(p00, p10, p11), (p00, p11, p01)]
            else:
                tris += [(p00, p10, p01), (p10, p11, p01)]
    tris = np.array(tris)
    E = set()
    for t in tris:
        for k in range(3):
            E.add(tuple(sorted((int(t[k]), int(t[(k + 1) % 3])))))
    return rest, tris, np.array(sorted(E))


def poids_depuis_histogramme(hist, x, band, n_band):
    """Valeurs wG des sommets de la bande, trié selon x, distribution = histogramme natif (quantiles)."""
    centres = (np.arange(10) + 0.5) / 10
    prob = np.array(hist, float)
    prob /= prob.sum()
    comptes = np.round(prob * n_band).astype(int)
    comptes[np.argmax(comptes)] += n_band - comptes.sum()
    valeurs = np.repeat(centres, comptes)
    w = np.zeros(len(x))
    w[x > band] = 1.0
    idx_band = np.where(np.abs(x) <= band)[0]
    ordre = idx_band[np.argsort(x[idx_band], kind="stable")]
    w[ordre] = valeurs[:len(ordre)] if len(valeurs) >= len(ordre) else np.resize(valeurs, len(ordre))
    return w


def mesures(rest, lbs, sq, tris, A, Mv, bande_mask):
    a, c = A[:, 0], A[:, 1]
    lr = np.linalg.norm(rest[a] - rest[c], axis=1)
    out = {}
    for nom, p in (("LBS", lbs), ("SQ", sq)):
        r = np.linalg.norm(p[a] - p[c], axis=1) / lr
        mb = bande_mask[a] & bande_mask[c]
        out[nom] = {"max": float(r.max()), "p99": float(np.quantile(r, 0.99)),
                    "max_bande": float(r[mb].max()) if mb.any() else None}
    st = S.stats(rest, lbs, sq, tris, A, Mv)
    out["SQ"]["retournements"] = st["SQ"]["retournements"]
    out["LBS"]["retournements"] = st["LBS"]["retournements"]
    out["SQ"]["compression_min_aire"] = st["triangles"]["aire_min_SQ"]
    out["LBS"]["compression_min_aire"] = st["triangles"]["aire_min_LBS"]
    return out


def cellule(geo, pds, tri, hist):
    h = ESP[geo]
    n = int(round(L_DOM / h)) + 1
    xs = np.linspace(-L_DOM / 2, L_DOM / 2, n)
    rest, tris, A = grille_T(xs, xs, tri)
    x = rest[:, 0]
    n_band = int(np.sum(np.abs(x) <= BANDE))
    wG = poids_depuis_histogramme(hist[pds], x, BANDE, n_band)
    RG = S.rot_y(np.radians(120))
    lbs = wG[:, None] * (rest @ RG.T) + (1 - wG)[:, None] * rest
    Mv = wG[:, None, None] * RG + (1 - wG)[:, None, None] * np.eye(3)
    Rsq = DEC.polaire_gen(Mv)
    sq = ARAP.solve_fixe(lbs, rest, A, Rsq, LAM)
    bande_mask = np.abs(x) <= BANDE + 1e-9
    res = mesures(rest, lbs, sq, tris, A, Mv, bande_mask)
    res["nb_sommets"] = int(len(rest))
    res["nb_aretes"] = int(len(A))
    res["espacement_m"] = float(h)
    res["nb_sommets_bande"] = n_band
    return res


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    desc = json.load(open(os.path.join(RACINE, "docs", "rapports", "skinning", "factorielle", "descriptif_morphologies.json")))
    hist = {"M": desc["masculin"]["histogramme_wG_mixtes_10_classes"],
            "F": desc["feminin"]["histogramme_wG_mixtes_10_classes"]}
    cellules = {}
    for geo in ("M", "F"):
        for pds in ("M", "F"):
            for tri in ("A", "B"):
                key = f"G{geo}_W{pds}_T{tri}"
                cellules[key] = cellule(geo, pds, tri, hist)
                r = cellules[key]
                print(key, "LBS max", round(r["LBS"]["max"], 3), "SQ max", round(r["SQ"]["max"], 3),
                      "SQ p99", round(r["SQ"]["p99"], 3), "bande SQ", round(r["SQ"]["max_bande"], 3),
                      "retour SQ", r["SQ"]["retournements"], "aire min SQ", round(r["SQ"]["compression_min_aire"], 3),
                      flush=True)

    def effet(f, metrique, src):
        """Effet principal du facteur f ('G','W','T') : moyenne(niveau 2) − moyenne(niveau 1)."""
        pos, neg = [], []
        for key, r in cellules.items():
            niveau = key[{"G": 1, "W": 4, "T": 7}[f]]
            v = src(r)
            (pos if niveau in ("F", "B") else neg).append(v)
        return float(np.mean(pos) - np.mean(neg))

    def interaction(f1, f2, src):
        """Interaction de premier ordre f1 × f2 : moitié de la différence des effets de f1 selon f2."""
        i1 = {"G": 1, "W": 4, "T": 7}[f1]
        i2 = {"G": 1, "W": 4, "T": 7}[f2]
        cell = {}
        for key, r in cellules.items():
            cell.setdefault((key[i1], key[i2]), []).append(src(r))
        m = {k: np.mean(v) for k, v in cell.items()}
        lv1 = sorted({k[0] for k in m})
        lv2 = sorted({k[1] for k in m})
        d_b = m[(lv1[1], lv2[1])] - m[(lv1[0], lv2[1])]
        d_a = m[(lv1[1], lv2[0])] - m[(lv1[0], lv2[0])]
        return float((d_b - d_a) / 2)

    metriques = {
        "max_SQ": lambda r: r["SQ"]["max"],
        "p99_SQ": lambda r: r["SQ"]["p99"],
        "max_bande_SQ": lambda r: r["SQ"]["max_bande"],
        "delta_max_SQ_moins_LBS": lambda r: r["SQ"]["max"] - r["LBS"]["max"],
        "delta_p99_SQ_moins_LBS": lambda r: r["SQ"]["p99"] - r["LBS"]["p99"],
        "compression_min_SQ": lambda r: r["SQ"]["compression_min_aire"],
        "retournements_SQ": lambda r: float(r["SQ"]["retournements"]),
    }
    effets = {}
    for nom, fn in metriques.items():
        effets[nom] = {
            "effet_geometrie_F_moins_M": effet("G", nom, fn),
            "effet_poids_F_moins_M": effet("W", nom, fn),
            "effet_triangulation_B_moins_A": effet("T", nom, fn),
            "interaction_geometrie_x_poids": interaction("G", "W", fn),
            "interaction_geometrie_x_triangulation": interaction("G", "T", fn),
            "interaction_poids_x_triangulation": interaction("W", "T", fn),
        }
    print(json.dumps(effets, indent=1, ensure_ascii=False), flush=True)
    with open(os.path.join(SORTIE, "plan_factoriel.json"), "w", encoding="utf-8") as f:
        json.dump({"cellules": cellules, "effets": effets, "parametres": {
            "espacement": ESP, "bande_m": BANDE, "domaine_m": L_DOM, "lambda": LAM, "rotation_G_deg": 120,
            "histogrammes_wG_mixtes": hist}}, f, indent=1, ensure_ascii=False)
    print("ECRIT", flush=True)
