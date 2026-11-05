"""Coude (phase 4, erreur 95) : volume d interpenetration entre bras et avant-bras, sphere de jonction retiree.
Dependance : scratchpad/arap/coude_calotte_cousue.py (donnees rest0, faces0, U_set, F_set, c, ax, J, Dom) ;
a lancer depuis ce dossier scratchpad. Pieces fermees par bouchons, orientation corrigee (trimesh.repair), booleens manifold.
Temoin positif : decalage 10 cm en +Z donne 46 cm3 (la methode detecte un chevauchement quand il existe)."""
"""Coude : volume d'interpénétration entre bras (fixe) et avant-bras (tourné), après retrait de la sphère de jonction.
Pièces fermées par bouchons (fan sur le centroïde de chaque boucle de bord) ; booléens manifold.
Mesure : vol(B - S) ∩ (F - S) : 0 = aucune traversée visible hors de la jointure."""
import numpy as np, trimesh
from collections import Counter
from scipy.spatial.transform import Rotation as Rot
exec(open('coude_calotte_cousue.py').read().split('print(f"rayons tubes')[0])
def aretes_bord_boucles(faces):
    cnt = Counter()
    for f in faces:
        for k in range(len(f)):
            cnt[tuple(sorted((f[k], f[(k+1) % len(f)])))] += 1
    return [e for e, n in cnt.items() if n == 1]
def fermer(V, faces):
    """Ferme chaque boucle de bord par un fan sur son centroïde."""
    bords = aretes_bord_boucles(faces)
    adj = {}
    for u, v in bords:
        adj.setdefault(u, []).append(v); adj.setdefault(v, []).append(u)
    seen = set(); boucles = []
    for s in adj:
        if s in seen: continue
        boucle = [s]; seen.add(s); prev = None; cur = s
        while True:
            nx = [x for x in adj[cur] if x != prev and x not in seen]
            if not nx: break
            prev, cur = cur, nx[0]; seen.add(cur); boucle.append(cur)
        boucles.append(boucle)
    V = list(V); nf = []
    for b in boucles:
        cen = np.mean(np.array(V)[b], axis=0); V.append(cen); ic = len(V) - 1
        for k in range(len(b)):
            nf.append([b[(k+1) % len(b)], b[k], ic])   # sens inverse de l'arête de bord : cohérence de surface
    return np.array(V), list(faces) + nf
def maille(V, faces):
    tri = []
    for f in faces:
        for k in range(1, len(f)-1): tri.append([f[0], f[k], f[k+1]])
    m = trimesh.Trimesh(V, np.array(tri), process=False)
    trimesh.repair.fix_winding(m); trimesh.repair.fix_inversion(m)
    return m
def piece(mask, Vpose):
    fs = [f for f in faces0 if all(mask[k] for k in f)]
    idx = -np.ones(len(rest0), int); idx[mask] = np.arange(mask.sum())
    fs2 = [[idx[k] for k in f] for f in fs]
    V, F = fermer(Vpose[mask], fs2)
    return maille(V, F)
U_mask = U_set.copy(); F_mask = F_set.copy()
def mesure(th, Rs):
    R = Rot.from_rotvec(ax*np.radians(th)).as_matrix()
    P = rest0.copy(); P[F_mask] = rest0[F_mask] @ R.T + (c - R @ c)
    bU = piece(U_mask, P); bF = piece(F_mask, P)
    sph = trimesh.creation.icosphere(subdivisions=3, radius=Rs); sph.apply_translation(c)
    if not (bU.is_watertight and bF.is_watertight):
        return None, bU.is_watertight, bF.is_watertight
    Ur = trimesh.boolean.difference([bU, sph], engine="manifold")
    Fr = trimesh.boolean.difference([bF, sph], engine="manifold")
    inter = trimesh.boolean.intersection([Ur, Fr], engine="manifold")
    return inter.volume * 1e6, True, True   # cm³
for Rs in (0.07,):
    for th in (0, 30, 60, 90, 120):
        v, fu, ff = mesure(th, Rs)
        print(f"Rs={Rs} θ={th}: volume d'interpénétration hors sphère = {v if v is None else round(v,2)} cm³ (bras fermé {fu}, avant-bras fermé {ff})", flush=True)
