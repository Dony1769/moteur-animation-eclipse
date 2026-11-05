"""Tests de visibilité (texturage maison), contre une vérité connue ou exacte.

1. Sphère (vérité connue : toutes les faces tournées vers la caméra sont visibles) : lancer de rayon exact = 100 %.
2. Corps de base : le lancer de rayon exact est la référence. Le tampon de profondeur n'est qu'un aperçu : son accord
   mesuré avec le lancer de rayon est reporté (≈ 90 % à 1 024 px), jamais présenté comme exact.
3. Le corps donne une part de faces visibles plausible (5 à 60 %) pour la vue avant.
"""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "human_generator"))
import corps as c
import visibilite as vis

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
NS = np.cross(P[FS[:, 1]]-P[FS[:, 0]], P[FS[:, 2]]-P[FS[:, 0]])
front = (NS @ [0, 0, 1.0]) > 0.05*np.linalg.norm(NS, axis=1)
sphere_exact = float((vis.visibilite_rayon(P, FS, [0, 0, 1.0]) & front).sum() / front.sum())

# 2. corps
V, F = c.charger_base()
Fm = np.asarray([f[:3] for f in F], dtype=int)
t0 = __import__("time").time()
vr = vis.visibilite_rayon(V, Fm, [0, 0, 1.0])
temps = __import__("time").time() - t0
vz = vis.visibilite(V, Fm, [0, 0, 1.0], res=1024, tol=0.01)
tourn = (np.cross(V[Fm[:, 1]]-V[Fm[:, 0]], V[Fm[:, 2]]-V[Fm[:, 0]]) @ [0, 0, 1.0]) > 0
accord_zbuf = float(np.mean(vz[tourn] == vr[tourn]))
part_visible = float(vr.mean())
rapport = dict(
    sphere_rayon_exact_part_visibles=round(sphere_exact, 4),
    corps_faces=int(len(Fm)), corps_visibles_vue_avant_rayon=round(part_visible, 4),
    corps_temps_rayon_s=round(temps, 1),
    corps_accord_tampon_1024_avec_rayon=round(accord_zbuf, 4),
    referente="rayon exact ; tampon = aperçu",
    statut="VALIDE_TECHNIQUE" if (sphere_exact == 1.0 and 0.05 <= part_visible <= 0.6) else "A_REVOIR")
assert sphere_exact == 1.0, rapport
assert 0.05 <= part_visible <= 0.6, rapport
out = Path(__file__).resolve().parents[2] / "docs" / "rapports" / "texturage_visibilite.json"
out.write_text(json.dumps(rapport, indent=2, ensure_ascii=False))
print(json.dumps(rapport, indent=2, ensure_ascii=False))
