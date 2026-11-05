"""Investigation géométrique de la dégradation de la hanche masculine (SQ et SQV1).

Étape A (identification) : pour chaque pose de test de hanche, sommets dont le maximum d'étirement incident dépasse
1,5 avec SQ ou SQV1, ou qui se dégradent de plus de 0,05 par rapport au LBS.
Étape B (géométrie) : position de repos, positions LBS / SQ / SQV1, déplacements, poids détaillés, distances aux
centres articulaires et aux segments osseux, arêtes et polygones incidents.
Étape C (carte spatiale) : répartition des défauts dans le repos (plans x-z et y-z).
Étape D (transformations) : vérification de la convention LBS, rotations LBS moyennée, os dominant, voisins.

Toutes les données viennent du fichier de poses masculin (poses2.npz) et du squelette extrait (étape 1). Aucun
paramètre n'est choisi ici : les poses sont celles de l'étape 3b/3c, la variante SQ celle de l'étape 3c.
"""
import importlib.util
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
RACINE = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
DONNEES = os.environ.get("ANATOMIE_DONNEES", "/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad")
SORTIE = os.path.join(RACINE, "docs", "rapports", "skinning", "investigation_hanche_masc")
NPZ = os.path.join(DONNEES, "skin", "poses2.npz")
JSON_SQ = os.path.join(RACINE, "docs", "rapports", "skinning", "anatomie", "squelette_masc.json")
SEUIL = 1.5
MARGE = 0.05


def charger(nom):
    spec = importlib.util.spec_from_file_location(nom, os.path.join(HERE, nom + ".py"))
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


P = charger("poses_articulaires")
M = charger("methodes")
Ms = charger("mesures")
ARAP = charger("experience_arap")
CV = charger("correction_volume")
EXP = charger("experience_corrections_articulaires")

TESTS = [("hanche_G", 75), ("hanche_G", 105), ("hanche_G", 120), ("hanche_D", 75), ("hanche_D", 120)]
NOM_OS = {"hanche_G": "LeftUpLeg", "hanche_D": "RightUpLeg"}


def ratio_par_sommet(pos, rest, A, N):
    """Maximum des rapports de longueur des arêtes incidentes, par sommet (N,)."""
    a, b = A[:, 0], A[:, 1]
    lr = np.linalg.norm(rest[a] - rest[b], axis=1)
    lp = np.linalg.norm(pos[a] - pos[b], axis=1)
    ok = lr > 1e-9
    r = np.zeros(len(A))
    r[ok] = lp[ok] / lr[ok]
    s = np.zeros(N)
    np.maximum.at(s, a, r)
    np.maximum.at(s, b, r)
    return s, r


def pose_test(z, noms, js, art, theta_deg):
    sens = EXP.signe_depuis_pose_reelle(z, noms, js, NOM_OS[art], "L_flex90" if art == "hanche_G" else "R_flex90")[0]
    centre, axe, chaine = P.articulation(js, EXP.prefixe(noms) + NOM_OS[art])
    T = P.transformation_articulation(centre, axe, np.radians(theta_deg), sens)
    pm = P.matrices_pose(z["bones_rest_monde"], noms, chaine, T)
    return pm, centre, chaine, sens


def tous_les_defauts():
    z = np.load(NPZ)
    noms = [str(n) for n in z["noms_os"]]
    rest, Wi, Ww, B = z["rest_monde"], z["W_idx"], z["W_w"], z["bones_rest_monde"]
    b, tot = z["b_boucle"], z["b_tot"]
    A = Ms.aretes(b, tot, len(rest))
    TRI = CV._triangles(b, tot)
    N = len(rest)
    sortie = {"poses": {}, "defauts_union": set()}
    for art, th in TESTS:
        pm, centre, chaine, sens = pose_test(z, noms, JSON_SQ, art, th)
        ref = M.calculer_toutes(rest, Wi, Ww, B, pm)[0]
        lbs = ref["LBS"]
        Rsq = ARAP.polaire(M.repere_rigide(Wi, Ww, B, pm))
        sq = ARAP.solve_fixe(lbs, rest, A, Rsq, 0.1)
        sqv1, _ = CV.corriger(sq, rest, Wi, Ww, b, tot, T=TRI, M=1)
        sqv3, _ = CV.corriger(sq, rest, Wi, Ww, b, tot, T=TRI, M=3)
        s_lbs, r_lbs = ratio_par_sommet(lbs, rest, A, N)
        s_sq, r_sq = ratio_par_sommet(sq, rest, A, N)
        s_v1, r_v1 = ratio_par_sommet(sqv1, rest, A, N)
        s_v3, _ = ratio_par_sommet(sqv3, rest, A, N)
        cle = f"{art}_{th}"
        # sommets dont SQV1 dépasse le seuil ET qui sont dégradés par rapport au LBS
        mauvais = np.where((s_v1 > SEUIL) & (s_v1 > s_lbs + MARGE))[0]
        mauvais_sq = np.where((s_sq > SEUIL) & (s_sq > s_lbs + MARGE))[0]
        sortie["poses"][cle] = {
            "max_LBS": float(s_lbs.max()), "max_SQ": float(s_sq.max()), "max_SQV1": float(s_v1.max()),
            "max_SQV3": float(s_v3.max()),
            "nb_sommets_degrades_SQV1": int(len(mauvais)), "nb_sommets_degrades_SQ": int(len(mauvais_sq)),
            "indices_SQV1": mauvais.tolist(), "indices_SQ": mauvais_sq.tolist(),
        }
        sortie["defauts_union"].update(mauvais.tolist())
        sortie["defauts_union"].update(mauvais_sq.tolist())
        print(f"{cle:12s} max LBS {s_lbs.max():.3f} | SQ {s_sq.max():.3f} | SQV1 {s_v1.max():.3f} | SQV3 {s_v3.max():.3f} "
              f"| sommets dégradés SQV1 {len(mauvais)} SQ {len(mauvais_sq)}", flush=True)
    sortie["defauts_union"] = sorted(sortie["defauts_union"])
    return z, noms, rest, Wi, Ww, B, b, tot, A, sortie


if __name__ == "__main__":
    os.makedirs(SORTIE, exist_ok=True)
    z, noms, rest, Wi, Ww, B, b, tot, A, sortie = tous_les_defauts()
    print("sommets défectueux (union) :", len(sortie["defauts_union"]), flush=True)
    with open(os.path.join(SORTIE, "etape_A_defauts.json"), "w", encoding="utf-8") as f:
        json.dump(sortie, f, indent=1, ensure_ascii=False)
    print("ECRIT", os.path.join(SORTIE, "etape_A_defauts.json"), flush=True)
