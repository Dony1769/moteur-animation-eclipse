"""Phase 3 : doigts du corps HBM (chaînes estimées à partir des lobes mesurés de la main).

Validations :
 - 5 doigts (pouce, index, majeur, annulaire, auriculaire) ;
 - longueurs de doigt dans une plage anatomique (0,05 à 0,11 m) ;
 - milieu de chaque phalange à l'intérieur du maillage (parité des intersections, direction X extérieure) ;
 - bilan : quels doigts sont mesurés, lesquels sont estimés (rien n'est caché).
Usage : blender -b --factory-startup --disable-autoexec -P engine/validation/test_hbm_doigts.py -- BUNDLE.blend RESULTAT_BRAS.json SORTIE.json SCRATCH
"""
import bpy, sys, json, os, shutil
import numpy as np
from mathutils import Vector, bvhtree, Matrix
import bmesh
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rigging"))
import doigts_hbm

argv = sys.argv[sys.argv.index("--") + 1:]
bundle, bras_json, sortie, scratch = argv[0], argv[1], argv[2], argv[3]
os.makedirs(scratch, exist_ok=True)
copie = os.path.join(scratch, "doigts_bundle.blend"); shutil.copy(bundle, copie)
bpy.ops.wm.open_mainfile(filepath=copie)
o = bpy.data.objects["GEO-body_male_realistic"]
P0 = [o.matrix_world @ v.co for v in o.data.vertices]
cx = (min(p.x for p in P0) + max(p.x for p in P0)) / 2
P = np.array([[p.x - cx, p.y, p.z] for p in P0])

J = json.load(open(bras_json))["joints"]["G"]
poignet = np.array(J["poignet"]); bout = np.array(J["bout_main"])
d = np.linalg.norm(P - poignet, axis=1)
main = P[(P[:, 0] > 0.05) & (d < 0.22)]

res = doigts_hbm.doigts(main, poignet, bout)
T = {}
T["nombre_doigts"] = {"ok": len(res) == 5, "detail": f"{len(res)} : {sorted(res)}"}
longs = {n: round(f["longueur_m"], 4) for n, f in res.items()}
hors = [n for n, L in longs.items() if not (0.05 <= L <= 0.11)]
T["longueurs_doigts"] = {"ok": not hors, "detail": f"longueurs {longs} ; hors plage {hors or 'aucun'}"}

# intérieur du maillage (même repère que test_hbm_bras)
bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world)
bm.transform(Matrix.Translation((-cx, 0.0, 0.0)))
bvh = bvhtree.BVHTree.FromBMesh(bm)
def interieur(pt, dr):
    n = 0; p = pt.copy()
    for _ in range(60):
        loc, nrm, idx, dist = bvh.ray_cast(p, dr)
        if loc is None: break
        n += 1; p = loc + dr * 1e-4
    return n % 2 == 1
# direction : épaisseur de la main (axe le plus fin), dans les deux sens ; un milieu est dedans
# si la parité est impaire dans les deux sens (une main fine rend le test en +X peu fiable)
_, _, nmain = doigts_hbm.repere(main, poignet, bout)
dehors, verifies, non_verifies = [], 0, []
for nom, f in res.items():
    for k, (a, b) in enumerate(f["phalanges"]):
        if k in f["segments_estimes"]:
            non_verifies.append(f"{nom}{k+1}")   # estimé : pas de ligne médiane mesurée, donc pas de test
            continue
        verifies += 1
        m = Vector(((np.array(a) + np.array(b)) / 2).tolist())
        dans = interieur(m, Vector(nmain.tolist())) and interieur(m, Vector((-nmain).tolist()))
        if not dans:
            dehors.append(f"{nom}{k+1}")
T["phalanges_dans_maillage"] = {"ok": not dehors and verifies > 0,
                                "detail": f"{verifies} phalanges mesurées testées ; hors du maillage : {dehors or 'aucune'} ; "
                                          f"non testées (estimées) : {non_verifies}"}
bm.free()

bilan = {n: {"mesure": f["mesure"], "estime": f["estime"]} for n, f in res.items()}
T["mesure_vs_estime"] = {"ok": True, "detail": json.dumps(bilan, ensure_ascii=False)}
out = {"doigts": {n: {"base": np.round(f["base"], 4).tolist(), "phalanges": [[np.round(a, 4).tolist(), np.round(b, 4).tolist()] for a, b in f["phalanges"]], "segments_estimes": f["segments_estimes"],
                      "mesure": f["mesure"], "estime": f["estime"], "longueur_m": round(f["longueur_m"], 4)} for n, f in res.items()},
       "tests": T}
json.dump(out, open(sortie, "w"), indent=2, ensure_ascii=False)
print("RESULTAT", "OK" if all(v["ok"] for v in T.values()) else "ECHEC " + ",".join(k for k, v in T.items() if not v["ok"]))
for k, v in T.items(): print("TEST", k, v)
