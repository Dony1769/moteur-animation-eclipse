"""Doigts du corps HBM : lignes médianes mesurées sur la main, phalanges placées dessus.

Principe (rien d'inventé sans signalement) :
 - repère de la main mesuré sur le maillage : u = poignet -> bout, n = épaisseur (axe le plus fin), v = largeur ;
 - les sommets distaux sont regroupés par largeur : un écart > SEPARATION = un doigt (lobe) ;
 - pour chaque lobe, la ligne médiane est mesurée (centroïde par tranche) : les articulations suivent
   le doigt réel, qui est courbé ;
 - l'auriculaire n'a pas de lobe propre quand le maillage le fond à l'annulaire : chaîne estimée.

Sortie : dict {nom: {"base", "phalanges": [(tete, queue)...], "mesure", "estime", "longueur_m"}}.
"""
import numpy as np

SEPARATION = 0.005                 # m : écart latéral qui sépare deux doigts
FRACTIONS = (0.45, 0.27, 0.28)     # proximale, médiane, distale (estimation anatomique)
A_MCP = 0.105                      # m du poignet à la base des doigts (estimation : paume)
RAYON_MAIN = 0.22                  # m : sommets de la main = dans cette distance du poignet
LARGEUR_DOIGT = 0.021             # m : largeur d'un doigt (estimation) ; un lobe plus large est découpé


def repere(P, poignet, bout):
    """Repère de la main : u (poignet -> bout), n (épaisseur, axe le plus fin), v (largeur)."""
    u = (bout - poignet) / np.linalg.norm(bout - poignet)
    C = P - P.mean(0)
    _, _, Vt = np.linalg.svd(C, full_matrices=False)
    n = Vt[2]
    v = np.cross(n, u); v /= np.linalg.norm(v)
    return u, v, n


def lobes(P, poignet, bout):
    """Groupes latéraux mesurés des sommets distaux : w_centre, w_min, w_max, a_max, t_centre."""
    u, v, n = repere(P, poignet, bout)
    rel = P - poignet
    a = rel @ u; w = rel @ v; t = rel @ n
    m = (a >= A_MCP) & (t > -0.06)
    ww, aa, tt = w[m], a[m], t[m]
    ordre = np.argsort(ww); ws, as_, ts = ww[ordre], aa[ordre], tt[ordre]
    out = []
    for g in np.split(np.arange(len(ws)), np.where(np.diff(ws) > SEPARATION)[0] + 1):
        if len(g) < 4:
            continue
        # un lobe plus large que deux doigts (doigts accolés) est découpé aux plus grands écarts
        k = max(1, int(round((ws[g].max() - ws[g].min()) / LARGEUR_DOIGT)))
        if k >= 2:
            ecarts = np.diff(ws[g])
            coupes = sorted(np.argsort(-ecarts)[:k - 1])
            morceaux = np.split(g, np.array(coupes) + 1)
        else:
            morceaux = [g]
        for h in morceaux:
            if len(h) < 4:
                continue
            out.append({"w_centre": float(ws[h].mean()), "w_min": float(ws[h].min()),
                        "w_max": float(ws[h].max()), "a_max": float(as_[h].max()),
                        "t_centre": float(ts[h].mean()), "nombre": int(len(h))})
    return out, u, v, n


def axe(P, poignet, u, v, n, g, a0, a1, pas=0.01):
    """Ligne médiane mesurée d'un lobe : centroïde (a, w, t) par tranche de a0 à a1."""
    rel = P - poignet
    a = rel @ u; w = rel @ v; t = rel @ n
    m = (w >= g["w_min"] - 1e-6) & (w <= g["w_max"] + 1e-6) & (a >= a0) & (a <= a1) & (t > -0.06)
    pts = []
    for s_ in np.arange(a0, a1 + 1e-9, pas):
        k = m & (np.abs(a - s_) < pas / 2)
        if k.sum() >= 3:
            pts.append((float(s_), float(w[k].mean()), float(t[k].mean())))
    return pts


def _chaine(poignet, u, v, n, lobe, a_mcp, phal, estime, mesure, ligne=None):
    """Phalanges d'un doigt. Si une ligne médiane mesurée est donnée, les articulations la suivent
    (abscisses curvilignes) ; sinon chaîne droite estimée."""
    if ligne is not None and len(ligne) >= 2:
        pts3 = np.array([poignet + u * a_ + v * w_ + n * t_ for a_, w_, t_ in ligne])
        seg = np.linalg.norm(np.diff(pts3, axis=0), axis=1)
        cum = np.concatenate([[0.0], np.cumsum(seg)])
        fr = FRACTIONS if phal == 3 else (0.5, 0.5)
        cibles = np.concatenate([[0.0], np.cumsum(fr)]) * cum[-1]
        joints = [np.array([np.interp(c, cum, pts3[:, k]) for k in range(3)]) for c in cibles]
    else:
        w = lobe["w_centre"]; t = lobe["t_centre"]
        base = poignet + u * a_mcp + v * w + n * t
        tip = poignet + u * lobe["a_max"] + v * w + n * t
        fr = FRACTIONS if phal == 3 else (0.5, 0.5)
        joints = [base]
        for f in fr:
            joints.append(joints[-1] + (tip - base) * f)
    segs = [(joints[k], joints[k + 1]) for k in range(len(joints) - 1)]
    return {"base": joints[0], "phalanges": segs, "mesure": mesure, "estime": estime,
            "longueur_m": float(sum(np.linalg.norm(b - a_) for a_, b in segs)),
            "segments_estimes": [] if ligne is not None else list(range(len(segs)))}


def doigts(P, poignet, bout):
    """Construit les chaînes de doigts à partir des lobes mesurés (du côté pouce vers l'extérieur).

    - pouce : lobe au bout le plus court, mesuré (base estimée à 6 cm du poignet) ;
    - index : lobe voisin du pouce, mesuré ; majeur : lobe au bout le plus long, mesuré ;
    - annulaire : lobe restant, mesuré ; si ce lobe est trop large pour un doigt (> 22 mm),
      l'auriculaire est estimé à son bord (80 % de la longueur du majeur, chaîne droite).
    """
    groupes, u, v, n = lobes(P, poignet, bout)
    if len(groupes) < 3:
        raise ValueError(f"{len(groupes)} lobe(s) seulement : main non mesurable")
    pouce = min(groupes, key=lambda g: g["a_max"])
    # doigts ordonnés depuis le pouce vers l'extérieur (valable pour les deux côtés)
    reste = sorted([g for g in groupes if g is not pouce], key=lambda g: abs(g["w_centre"] - pouce["w_centre"]))
    majeur = max(reste, key=lambda g: g["a_max"])
    autres = [g for g in reste if g is not majeur]
    index = autres[0]
    restant = autres[1] if len(autres) > 1 else None

    res = {}
    res["pouce"] = _chaine(poignet, u, v, n, pouce, a_mcp=0.06, phal=2,
                           estime=["base du pouce estimée à 6 cm du poignet (paume non résolue)"], mesure=True,
                           ligne=axe(P, poignet, u, v, n, pouce, 0.06, pouce["a_max"]))
    # le premier segment du pouce (base) n'a pas de ligne médiane fiable : marqué estimé
    res["pouce"]["segments_estimes"] = [0]
    res["index"] = _chaine(poignet, u, v, n, index, a_mcp=A_MCP, phal=3, estime=[], mesure=True,
                           ligne=axe(P, poignet, u, v, n, index, A_MCP, index["a_max"]))
    res["majeur"] = _chaine(poignet, u, v, n, majeur, a_mcp=A_MCP, phal=3, estime=[], mesure=True,
                            ligne=axe(P, poignet, u, v, n, majeur, A_MCP, majeur["a_max"]))
    if restant is not None:
        large = restant["w_max"] - restant["w_min"] > 0.022
        res["annulaire"] = _chaine(poignet, u, v, n, restant, a_mcp=A_MCP, phal=3,
                                   estime=(["lobe large : annulaire et auriculaire possiblement fusionnés"]
                                           if large else []), mesure=True,
                                   ligne=axe(P, poignet, u, v, n, restant, A_MCP, restant["a_max"]))
        if large:
            faux = dict(restant)
            faux["w_centre"] = restant["w_min"] - 0.009
            faux["a_max"] = A_MCP + 0.8 * (majeur["a_max"] - A_MCP)
            res["auriculaire"] = _chaine(poignet, u, v, n, faux, a_mcp=A_MCP, phal=3,
                                         estime=["position latérale et longueur estimées (80 % du majeur)"],
                                         mesure=False, ligne=None)
    return res
