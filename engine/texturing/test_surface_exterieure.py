"""Tests de classification extérieure/intérieure (règle de Takayama, texturage maison).

1. Sphère (vérité connue) : toutes les faces non dégénérées sont extérieures ; aucune à retourner.
2. Corps de base : cohérence avec la visibilité exacte. Toute face vue par une des six vues (lancer de rayon,
   visibilite_rayon) doit être classée extérieure. Mesure : part des faces internes et des faces dégénérées.
"""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "human_generator"))
import corps as c
import visibilite as vis
import surface_exterieure as se

# 1. sphère
nu, nv = 60, 30
th = np.linspace(0, np.pi, nv); ph = np.linspace(0, 2*np.pi, nu, endpoint=False)
P = np.array([[np.sin(t)*np.cos(p), np.cos(t), np.sin(t)*np.sin(p)] for t in th for p in ph])
FS = []
for j in range(nv-1):
    for i in range(nu):
        a = j*nu+i; b = j*nu+(i+1) % nu; cc = (j+1)*nu+i; d = (j+1)*nu+(i+1) % nu
        FS.append([a, b, cc]); FS.append([b, d, cc])
FS = np.array(FS)
ext_s, _, _, ret_s = se.classer(P, FS, points_par_face=2, directions=32)
aire_s = 0.5*np.linalg.norm(np.cross(P[FS[:, 1]]-P[FS[:, 0]], P[FS[:, 2]]-P[FS[:, 0]]), axis=1)
non_degen = aire_s >= 1e-12
sphere_ok = bool(ext_s[non_degen].all()) and int(ret_s.sum()) == 0

# 2. corps
V, F = c.charger_base()
Fm = np.asarray([f[:3] for f in F], dtype=int)
ext, cf, cb, ret = se.classer(V, Fm, points_par_face=2, directions=32)
vues = {}
for nom, dvec in (("avant", [0, 0, 1.]), ("arriere", [0, 0, -1.]), ("droite", [1., 0, 0]), ("gauche", [-1., 0, 0]),
                  ("dessus", [0, 1., 0]), ("dessous", [0, -1., 0])):
    vues[nom] = vis.visibilite_rayon(V, Fm, dvec)
vu_par_une_vue = np.zeros(len(Fm), dtype=bool)
for v in vues.values():
    vu_par_une_vue |= v
incoherentes = int((vu_par_une_vue & ~ext).sum())
aire = 0.5*np.linalg.norm(np.cross(V[Fm[:, 1]]-V[Fm[:, 0]], V[Fm[:, 2]]-V[Fm[:, 0]]), axis=1)
rapport = dict(
    sphere_exterieures_hors_degenerees=sphere_ok, sphere_a_retourner=int(ret_s.sum()),
    corps_faces=int(len(Fm)), corps_exterieures=int(ext.sum()), corps_interieures=int((~ext).sum()),
    corps_degenerees=int((aire < 1e-12).sum()), corps_a_retourner=int(ret.sum()),
    faces_vues_par_une_des_6_vues=int(vu_par_une_vue.sum()), incoherences_vues_non_exterieures=incoherentes,
    statut="VALIDE_TECHNIQUE" if (sphere_ok and incoherentes == 0) else "A_REVOIR",
    limite="règle de Takayama : 2 points × 32 directions par face ; résultat dépend de l'échantillonnage (graine fixe)")
assert sphere_ok, rapport
assert incoherentes == 0, rapport
out = Path(__file__).resolve().parents[2] / "docs" / "rapports" / "texturage_surface_exterieure.json"
out.write_text(json.dumps(rapport, indent=2, ensure_ascii=False))
print(json.dumps(rapport, indent=2, ensure_ascii=False))
