"""Tests des métriques locales sur géométries synthétiques à résultat connu (phase 4, priorité 1).
Chaque métrique a au moins un test positif (défaut présent, détecté) et un test négatif (absence, rien détecté).
Les attendus sont calculés à la main ; ils ne sont pas réglés sur les sorties du code.
Usage : python3 engine/validation/skinning/test_metriques_synthetiques.py
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import geometries_synthetiques as G  # noqa: E402
import metriques_locales as ML  # noqa: E402
import mesures as Ms  # noqa: E402

RES = []


def verifier(nom, cond, detail=""):
    RES.append((nom, bool(cond), detail))


def rotation_x(deg):
    t = np.radians(deg)
    return np.array([[1, 0, 0], [0, np.cos(t), -np.sin(t)], [0, np.sin(t), np.cos(t)]])


def cube(n=4, cote=1.0, centre=(0, 0, 0)):
    p, b, t = G.cube_subdivise(n, cote, centre)
    return p, b, t, G.aretes_de(b, t, len(p))


# ---------- 1. translation rigide ----------
def test_translation():
    rest, b, t, A = cube()
    pos = rest + np.array([0.3, 0.0, 0.0])
    d = ML.defauts(pos, rest, b, t, A)
    verifier("T1a_translation_pas_d_etirement", abs(d["etirement_max"] - 1) < 1e-9 and d["aretes_etirees_>1.1"] == 0,
             f"max {d['etirement_max']:.12f}")
    _, _, r = ML.separer_rigide(pos, rest)
    verifier("T1b_translation_residu_nul", r.max() < 1e-9, f"résidu max {r.max():.2e} m")
    v = ML.volume_local(pos, rest, b, t)["variation_volume_total"]
    verifier("T1c_translation_volume_inchange", abs(v) < 1e-9, f"variation {v:.2e}")
    # négatif : une bosse locale doit être vue par le résidu
    bosse = pos.copy()
    k = int(np.argmin(np.linalg.norm(rest - np.array([0.5, 0, 0]), axis=1)))
    bosse[k] += np.array([0.0, 0.0, 0.02])
    _, _, r2 = ML.separer_rigide(bosse, rest)
    verifier("T1d_bosse_detectee_par_residu", r2.max() > 0.002, f"résidu max {r2.max()*1e3:.2f} mm (bosse 20 mm)")


# ---------- 2. rotation rigide ----------
def test_rotation():
    rest, b, t, A = cube()
    R = rotation_x(120)
    pos = rest @ R.T
    d = ML.defauts(pos, rest, b, t, A)
    verifier("R1a_rotation_pas_d_etirement", abs(d["etirement_max"] - 1) < 1e-9 and abs(d["compression_min"] - 1) < 1e-9,
             f"max {d['etirement_max']:.12f} min {d['compression_min']:.12f}")
    _, _, r = ML.separer_rigide(pos, rest)
    verifier("R1b_rotation_residu_nul", r.max() < 1e-9, f"résidu max {r.max():.2e} m")
    Mv = np.stack([R] * len(rest))
    fl, _ = Ms.masque_retournes(pos, rest, b, t, Mv)
    verifier("R1c_rotation_zero_retournement_avec_repere", fl.sum() == 0, f"{int(fl.sum())}")
    fl0, _ = Ms.masque_retournes(pos, rest, b, t, None)
    verifier("R1d_rotation_faux_retournements_sans_repere", fl0.sum() > 0,
             f"{int(fl0.sum())} (régression entrée 147)")
    # négatif : rotation suivie d'une dilatation en x : le résidu doit être non nul
    pos2 = (rest * np.array([1.2, 1, 1])) @ R.T
    _, _, r2 = ML.separer_rigide(pos2, rest)
    verifier("R1e_non_rigide_residu_positif", r2.max() > 0.05, f"résidu max {r2.max():.3f} m")


# ---------- 3. échelle uniforme ----------
def test_echelle():
    rest, b, t, A = cube()
    s = 1.2
    pos = rest * s
    d = ML.defauts(pos, rest, b, t, A)
    verifier("E1a_echelle_etirement_exact", abs(d["etirement_max"] - s) < 1e-9 and abs(d["compression_min"] - s) < 1e-9,
             f"max {d['etirement_max']:.9f}")
    v = ML.volume_local(pos, rest, b, t)["variation_volume_total"]
    verifier("E1b_echelle_volume_s3", abs(v - (s ** 3 - 1)) < 1e-9, f"variation {v:.9f} attendu {s**3-1:.9f}")
    # négatif : échelle 1 => rien
    d1 = ML.defauts(rest, rest, b, t, A)
    verifier("E1c_sans_echelle_rien_detecte", d1["aretes_etirees_>1.1"] == 0 and d1["aretes_comprimees_<0.9"] == 0,
             "aucune arête signalée")


# ---------- 4. compression locale ----------
def test_compression():
    rest, b, t, A = cube()
    c = np.array([0.5, 0.0, 0.0])
    pos = rest.copy()
    dist = np.linalg.norm(rest - c, axis=1)
    m = dist < 0.3
    pos[m] = c + (rest[m] - c) * 0.7
    d = ML.defauts(pos, rest, b, t, A)
    verifier("C1a_compression_detectee", d["aretes_comprimees_<0.9"] > 0 and d["compression_min"] < 0.8,
             f"min {d['compression_min']:.3f} ; arêtes < 0,9 : {d['aretes_comprimees_<0.9']}")
    loc = d["localisation_compression_m"]
    ok_loc = loc is not None and np.linalg.norm(np.array(loc) - c) < 0.3
    verifier("C1b_compression_localisee", ok_loc, f"centre détecté {np.round(loc,3) if loc else None} attendu {c}")
    # Attendu calculé à la main : les 4 arêtes de la bordure (sommet fixe à 0,5 m, sommet déplacé à 0,175 m)
    # passent de 0,25 à 0,325 m, soit un rapport exact de 1,30. Ce n'est pas un bug : la déformation de test
    # étire aussi la bordure de la cuvette. Le test vérifie la valeur, le nombre d'arêtes et la localisation.
    verifier("C1c_bordure_etiree_valeur_exacte", d["aretes_etirees_>1.1"] == 4 and abs(d["etirement_max"] - 1.3) < 1e-9,
             f"arêtes > 1,1 : {d['aretes_etirees_>1.1']} ; max {d['etirement_max']:.9f} (attendu 4 et 1,300000000)")
    # négatif : échelle uniforme > 1 : aucune compression
    d2 = ML.defauts(rest * 1.3, rest, b, t, A)
    verifier("C1d_pas_de_compression_sans_defaut", d2["aretes_comprimees_<0.9"] == 0, "0 arête")


# ---------- 5. étirement local sur une très petite zone ----------
def test_etirement_petit():
    rest, b, t, A = cube()
    # sommet du centre de la face x = +0,5 : déplacé de 0,125 m vers l'extérieur
    v = int(np.argmin(np.linalg.norm(rest - np.array([0.5, 0.0, 0.0]), axis=1)))
    pos = rest.copy()
    pos[v] += np.array([0.125, 0.0, 0.0])
    d = ML.defauts(pos, rest, b, t, A)
    attendu = np.sqrt(0.125 ** 2 + 0.25 ** 2) / 0.25  # 1,118, arêtes de 0,25 m vers les 4 voisins
    verifier("S1a_etirement_valeur_exacte", abs(d["etirement_max"] - attendu) < 1e-6,
             f"max {d['etirement_max']:.6f} attendu {attendu:.6f}")
    verifier("S1b_zone_limitee_aux_4_aretes", d["aretes_etirees_>1.1"] == 4,
             f"arêtes > 1,1 : {d['aretes_etirees_>1.1']} (attendu 4)")
    verifier("S1c_sommet_le_plus_touche_identifie", d["pires_sommets"][0]["sommet"] == v and d["pires_sommets"][0]["aretes_etirees"] == 4,
             f"pire sommet {d['pires_sommets'][0]['sommet']} attendu {v}")
    verifier("S1d_localisation_pres_du_sommet", np.linalg.norm(np.array(d["localisation_etirement_m"]) - pos[v]) < 0.13,
             f"localisation {np.round(d['localisation_etirement_m'],3)}")
    d0 = ML.defauts(rest, rest, b, t, A)
    verifier("S1e_negatif_sans_deplacement", d0["aretes_etirees_>1.1"] == 0 and d0["etirement_max"] < 1 + 1e-9, "rien")


# ---------- 6. intersections ----------
def fusion(a, b_):
    pa, ba, ta = a
    pb, bb, tb = b_
    p = np.vstack([pa, pb])
    bo = np.concatenate([ba, bb + len(pa)])
    to = np.concatenate([ta, tb])
    return p, bo, to


def test_intersections():
    pa, ba, ta = G.cube_subdivise(4, 1.0)
    pb, bb, tb = G.cube_subdivise(2, 0.2)
    p, bo, to = fusion((pa, ba, ta), (pb, bb, tb))
    na = len(pa)
    ma = np.zeros(len(p), bool); ma[:na] = True
    mb = ~ma
    r = ML.intersections(p, bo, to, ma, mb)
    verifier("I1a_petit_cube_dans_grand_detecte", r["sommets_penetrants"] == len(pb),
             f"{r['sommets_penetrants']} sur {len(pb)}")
    verifier("I1b_profondeur_exacte", abs(r["profondeur_max_m"] - 0.4) < 1e-6,
             f"profondeur max {r['profondeur_max_m']:.6f} attendu 0,400000")
    verifier("I1c_localisation_centre", np.linalg.norm(np.array(r["localisation_m"])) < 1e-6,
             f"localisation {np.round(r['localisation_m'],6)}")
    # négatif : cube B à l'extérieur (écart de 0,3 m)
    pb2 = pb + np.array([0.8, 0, 0])
    p2, bo2, to2 = fusion((pa, ba, ta), (pb2, bb, tb))
    r2 = ML.intersections(p2, bo2, to2, ma, mb)
    verifier("I1d_separes_rien_detecte", r2["sommets_penetrants"] == 0, f"{r2['sommets_penetrants']}")


# ---------- 7. volume local ----------
def test_volume_local():
    rest, b, t, A = cube()
    d = 0.05
    pos = rest.copy()
    m = rest[:, 0] > 0.49
    pos[m, 0] += d  # face x = +0,5 translatée de 0,05 : volume 1 -> 1,05 (prisme)
    v = ML.volume_local(pos, rest, b, t)["variation_volume_total"]
    verifier("V1a_volume_face_translatee", abs(v - d) < 1e-6, f"variation {v:.6f} attendu {d}")
    v0 = ML.volume_local(rest, rest, b, t)["variation_volume_total"]
    verifier("V1b_negatif_sans_changement", abs(v0) < 1e-12, f"{v0:.2e}")


# ---------- 8. séparation rigide / déformation : cas non cubiques ----------
def test_separation_scale_mix():
    rest, b, t, A = cube()
    R = rotation_x(45)
    pos = (rest * 1.0) @ R.T + np.array([0.2, 0.1, 0.0])
    _, _, r = ML.separer_rigide(pos, rest)
    verifier("P1_rigide_quelconque_residu_nul", r.max() < 1e-9, f"{r.max():.2e}")


# ---------- 9. résidu par os dominant (articulation) ----------
def test_residu_os_dominant():
    rest, b, t, A = cube()
    Rz = np.array([[0, -1, 0], [1, 0, 0], [0, 0, 1.0]])  # rotation de 90° autour de z
    T = np.stack([np.eye(4), np.eye(4)])
    T[1, :3, :3] = Rz
    Wi = np.tile(np.array([0, 1], dtype=np.int64), (len(rest), 1))  # colonne 0 -> os 0, colonne 1 -> os 1
    Ww = np.zeros((len(rest), 2))
    # sommets côté x < 0 : os 0 dominant ; côté x > 0 : os 1 dominant (poids 1)
    Ww[:, 0] = np.where(rest[:, 0] < 0, 1.0, 0.0)
    Ww[:, 1] = np.where(rest[:, 0] < 0, 0.0, 1.0)
    pos = np.where((rest[:, 0] < 0)[:, None], rest, rest @ Rz.T)
    r = ML.residu_os_dominant(pos, rest, Wi, Ww, T)
    verifier("D1a_mouvement_rigide_de_l_os_residu_nul", r.max() < 1e-12, f"résidu max {r.max():.2e}")
    # négatif : mélange 50/50 (LBS) : le résidu vaut l'écart au mouvement rigide de l'os dominant
    Ww2 = np.full((len(rest), 2), 0.5)
    pos2 = 0.5 * rest + 0.5 * (rest @ Rz.T)
    r2 = ML.residu_os_dominant(pos2, rest, Wi, Ww2, T)
    attendu = 0.5 * np.linalg.norm(rest - rest @ Rz.T, axis=1)
    verifier("D1b_melange_residu_exact", np.abs(r2 - attendu).max() < 1e-9,
             f"écart au calcul à la main {np.abs(r2 - attendu).max():.2e} ; résidu max {r2.max():.4f}")
    verifier("D1c_melange_residu_positif", r2.max() > 0.01, f"résidu max {r2.max():.4f} m")


# ---------- 10. correction locale de volume (Rohmer et al. 2008) ----------
def test_correction_volume():
    import correction_volume as CV
    rest, b, t, A = cube()
    T = CV._triangles(b, t)
    pos = rest.copy()
    m = rest[:, 0] > 0.49
    pos[m, 0] -= 0.05  # face enfoncée : volume perdu de 5 %
    Wi = np.zeros((len(rest), 1), dtype=np.int64)
    Ww = np.ones((len(rest), 1))
    p3, d3 = CV.corriger(pos, rest, Wi, Ww, b, t, T=T, M=3, G=0.0)
    verifier("K1a_correction_volume_restaure", abs(d3["relatif_apres"]) < 0.01,
             f"avant {d3['relatif_avant']:+.4f} ; après 3 étapes {d3['relatif_apres']:+.2e}")
    p0, d0 = CV.corriger(rest, rest, Wi, Ww, b, t, T=T, M=3, G=0.0)
    verifier("K1b_sans_defaut_aucune_modification", np.abs(p0 - rest).max() < 1e-12,
             f"déplacement max {np.abs(p0 - rest).max():.2e}")
    # localité : un sommet pur (poids 1 sur un os) ne bouge pas quand gamma = 0 pour lui
    Wi2 = np.zeros((len(rest), 2), dtype=np.int64); Wi2[:, 1] = 1
    Ww2 = np.zeros((len(rest), 2)); Ww2[:, 0] = np.where(rest[:, 0] > 0, 1.0, 0.5); Ww2[:, 1] = 1 - Ww2[:, 0]
    p5, _ = CV.corriger(pos, rest, Wi2, Ww2, b, t, T=T, M=1, G=1.0)
    purs = np.where(rest[:, 0] > 0)[0]
    verifier("K1c_os_pur_non_deplace", np.abs(p5[purs] - pos[purs]).max() < 1e-12,
             f"déplacement max sur sommets purs {np.abs(p5[purs] - pos[purs]).max():.2e}")


def main():
    test_translation()
    test_rotation()
    test_echelle()
    test_compression()
    test_etirement_petit()
    test_intersections()
    test_volume_local()
    test_separation_scale_mix()
    test_residu_os_dominant()
    test_correction_volume()
    for nom, ok, d in RES:
        print(("OK   " if ok else "ECHEC") + " " + nom + " : " + d)
    echecs = [n for n, ok, _ in RES if not ok]
    print("RESULTAT", "OK" if not echecs else "ECHEC " + ",".join(echecs))
    return 0 if not echecs else 1


if __name__ == "__main__":
    sys.exit(main())
