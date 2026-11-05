"""Tests du banc de skinning (phase 4). Exécution : python3 engine/validation/skinning/test_skinning.py [POSES.npz]

Tests synthétiques (sans Blender) :
  1. quaternion -> matrice : aller-retour exact sur des rotations aléatoires ;
  2. LBS : égal à la formule explicite somme_k w_k (R_k p + t_k) ;
  3. DQS : égal à LBS pour un seul os, et pour des transformations de pure translation ;
  4. hybride : a = 0 donne LBS, a = 1 donne DQS ;
  5. métrique de retournement : un cube tourné de 120° n'a aucun polygone retourné avec le repère rigide,
     et en a avec la comparaison au repos brut (régression de l'entrée 147) ;
  6. volume d'un cube unitaire = 1 (signe et triangulation).
Test sur données réelles (si POSES.npz est fourni) :
  7. LBS reconstruit depuis les matrices de pose coïncide avec la déformation évaluée par Blender (seuil 1e-5 m, fixé
     avant la mesure ; la mesure donne 4,5e-7 m).
Les seuils ne sont pas réglés pour faire passer un test : ils mesurent la justesse de l'implémentation.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import methodes as M  # noqa: E402
import mesures as Ms  # noqa: E402

RESULTATS = []


def verifier(nom, cond, detail=""):
    RESULTATS.append((nom, bool(cond), detail))


def rotation_aleatoire(rng):
    q = rng.normal(size=4)
    q /= np.linalg.norm(q)
    w, x, y, z = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def test_quaternion(rng):
    erreur = 0.0
    for _ in range(200):
        R = rotation_aleatoire(rng)
        Q = M.quat_depuis_matrice(R[None])[0]
        w, x, y, z = Q
        R2 = np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                       [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                       [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])
        erreur = max(erreur, np.abs(R - R2).max())
    verifier("1_quaternion_aller_retour", erreur < 1e-9, f"erreur max {erreur:.2e}")


def scenario(rng, J=4, N=50, K=3):
    pos = rng.normal(size=(N, 3))
    W_idx = np.stack([rng.choice(J, size=K, replace=False) for _ in range(N)])
    W_w = rng.random((N, K))
    W_w /= W_w.sum(1, keepdims=True)
    R = np.stack([rotation_aleatoire(rng) for _ in range(J)])
    t = rng.normal(size=(J, 3)) * 0.3
    return pos, W_idx, W_w, R, t


def test_lbs_formule(rng):
    pos, Wi, Ww, R, t = scenario(rng)
    attendu = np.zeros_like(pos)
    for i in range(len(pos)):
        for k in range(Wi.shape[1]):
            j = Wi[i, k]
            attendu[i] += Ww[i, k] * (R[j] @ pos[i] + t[j])
    erreur = np.abs(M.lbs(pos, Wi, Ww, R, t) - attendu).max()
    verifier("2_lbs_formule", erreur < 1e-12, f"erreur {erreur:.2e}")


def test_dqs_cas_limites(rng):
    pos, Wi, Ww, R, t = scenario(rng)
    Q = M.quat_depuis_matrice(R)
    # un seul os par sommet
    Wi1 = Wi[:, :1].copy()
    Ww1 = np.ones_like(Ww[:, :1])
    e1 = np.abs(M.dqs(pos, Wi1, Ww1, Q, t) - M.lbs(pos, Wi1, Ww1, R, t)).max()
    verifier("3a_dqs_un_os_egal_lbs", e1 < 1e-9, f"erreur {e1:.2e}")
    # transformations de pure translation
    Rid = np.stack([np.eye(3)] * R.shape[0])
    Qid = M.quat_depuis_matrice(Rid)
    e2 = np.abs(M.dqs(pos, Wi, Ww, Qid, t) - M.lbs(pos, Wi, Ww, Rid, t)).max()
    verifier("3b_dqs_translation_egal_lbs", e2 < 1e-9, f"erreur {e2:.2e}")


def test_hybride_extremites(rng):
    pos, Wi, Ww, R, t = scenario(rng)
    Q = M.quat_depuis_matrice(R)
    L = M.lbs(pos, Wi, Ww, R, t)
    D = M.dqs(pos, Wi, Ww, Q, t)
    e0 = np.abs(M.hybride(L, D, 0.0) - L).max()
    e1 = np.abs(M.hybride(L, D, 1.0) - D).max()
    verifier("4_hybride_extremites", e0 < 1e-12 and e1 < 1e-12, f"erreurs {e0:.2e} {e1:.2e}")


def cube():
    """Cube unitaire : 8 sommets, 6 faces quadrilatères orientées vers l'extérieur."""
    p = np.array([[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 1], [1, 0, 1], [1, 1, 1], [0, 1, 1]], float)
    faces = [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [2, 3, 7, 6], [1, 2, 6, 5], [0, 4, 7, 3]]
    boucle = np.array([v for f in faces for v in f], dtype=np.int64)
    tot = np.array([4] * 6, dtype=np.int64)
    return p, boucle, tot


def test_retournement_rotation(rng):
    p, b, tot = cube()
    c = p.mean(0)
    th = np.radians(120)
    Rx = np.array([[1, 0, 0], [0, np.cos(th), -np.sin(th)], [0, np.sin(th), np.cos(th)]])
    pos = (p - c) @ Rx.T + c
    Mv = np.stack([Rx] * len(p))
    brut, _ = Ms.masque_retournes(pos, p, b, tot, None)
    rigide, _ = Ms.masque_retournes(pos, p, b, tot, Mv)
    verifier("5_retournement_rigide_zero", rigide.sum() == 0, f"rigide {int(rigide.sum())} ; brut {int(brut.sum())}")
    verifier("5b_brut_detecte_faux_positifs", brut.sum() > 0, f"brut {int(brut.sum())} (entrée 147 : faux positifs)")


def test_volume_cube():
    p, b, tot = cube()
    v = Ms._volume(p, b, tot)
    verifier("6_volume_cube_unitaire", abs(v - 1.0) < 1e-12, f"volume {v:.6f}")


def test_lbs_vs_blender(npz):
    d = np.load(npz)
    nom = os.path.basename(npz)
    rest, Wi, Ww, B = d["rest_monde"], d["W_idx"], d["W_w"], d["bones_rest_monde"]
    pire = 0.0
    nb = 0
    for k in d.files:
        if k.endswith("__os") and (k[:-4] + "__ctrl") in d.files:
            pos, _ = M.calculer_toutes(rest, Wi, Ww, B, d[k])
            pire = max(pire, float(np.abs(pos["LBS"] - d[k[:-4] + "__ctrl"]).max()))
            nb += 1
    verifier(f"7_lbs_vs_blender[{nom}]", pire < 1e-5, f"{nb} poses ; erreur max {pire:.2e} m")


def test_normalisation_poids(rng):
    """Entrée 152 : Blender normalise les poids par leur somme. Un sommet dont les poids totalisent 0,5 doit donner
    le même résultat que le même sommet avec des poids doublés (et non un rétrécissement vers l'origine)."""
    pos, Wi, Ww, R, t = scenario(rng)
    p1 = M.lbs(pos, Wi, Ww, R, t)
    p2 = M.lbs(pos, Wi, 0.5 * Ww, R, t)
    verifier("8_normalisation_poids_comme_blender", np.abs(p1 - p2).max() < 1e-12,
             f"écart {np.abs(p1 - p2).max():.2e}")


def main():
    rng = np.random.default_rng(0)
    test_quaternion(rng)
    test_lbs_formule(rng)
    test_dqs_cas_limites(rng)
    test_hybride_extremites(rng)
    test_retournement_rotation(rng)
    test_volume_cube()
    test_normalisation_poids(rng)
    for chemin in sys.argv[1:]:
        test_lbs_vs_blender(chemin)
    for nom, ok, d in RESULTATS:
        print(("OK   " if ok else "ECHEC") + " " + nom + " : " + d)
    echecs = [n for n, ok, _ in RESULTATS if not ok]
    print("RESULTAT", "OK" if not echecs else "ECHEC " + ",".join(echecs))
    return 0 if not echecs else 1


if __name__ == "__main__":
    sys.exit(main())
