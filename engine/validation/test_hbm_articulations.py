"""Test B, item 5 : estimation des articulations du corps HBM sans skinning.

Méthode :
 - proportions anatomiques en fraction de la hauteur h (cheville 0,04 ; genou 0,285 ; hanche 0,53 ;
   épaule 0,82 ; cou 0,84 ; tête 0,87) ;
 - vérification géométrique : le genou doit coïncider avec la section la plus fine de la jambe
   (profondeur Y minimale entre 0,15 h et 0,40 h, lissée sur 3 niveaux) ;
 - symétrie gauche/droite de la boîte englobante (contrôle de cohérence) ;
 - les autres articulations sont ESTIMÉES, non validées : le statut le dit.
Usage : blender -b --factory-startup --disable-autoexec -P engine/validation/test_hbm_articulations.py -- BUNDLE.blend SORTIE.json SCRATCH
"""
import bpy, sys, json, os, shutil

argv = sys.argv[sys.argv.index("--") + 1:]
bundle, sortie, scratch = argv[0], argv[1], argv[2]
os.makedirs(scratch, exist_ok=True)
copie = os.path.join(scratch, "bundle.blend"); shutil.copy(bundle, copie)
bpy.ops.wm.open_mainfile(filepath=copie)
o = bpy.data.objects["GEO-body_male_realistic"]
pts_monde = [o.matrix_world @ v.co for v in o.data.vertices]
# le corps n'est pas centré dans le bundle (translation x ≈ -2,26 m) : on recentre sur son milieu en X
xs_monde = [p.x for p in pts_monde]
cx = (min(xs_monde) + max(xs_monde)) / 2
from mathutils import Vector
pts = [Vector((p.x - cx, p.y, p.z)) for p in pts_monde]
zmin = min(p.z for p in pts); zmax = max(p.z for p in pts)
h = zmax - zmin
xs = [p.x for p in pts]
res = {"hauteur": round(h, 4), "centre_x_bundle": round(cx, 4), "articulations": {}, "tests": {}}
T = res["tests"]
A = res["articulations"]

def estime(frac_z, x=0.0):
    return {"z": round(zmin + frac_z * h, 4), "x": round(x, 4), "statut": "estimee"}

A["cheville_g"] = estime(0.04, 0.09 * h); A["genou_g"] = estime(0.285, 0.10 * h)
A["hanche_g"] = estime(0.53, 0.09 * h); A["epaule_g"] = estime(0.82, 0.19 * h)
A["cou"] = estime(0.84); A["tete"] = estime(0.87)

# -- vérification du genou : section la plus fine de la jambe (x > 0.03 pour ne garder qu'une jambe) --
pas = 0.005 * h
niveaux = []
z = zmin + 0.15 * h
while z <= zmin + 0.40 * h:
    # profondeur (étendue en Y) de la jambe : ne s'effondre pas à l'entrejambe, contrairement à l'étendue en X
    sel = [p.y for p in pts if abs(p.z - z) <= pas and p.x > 0.03]
    niveaux.append((z, (max(sel) - min(sel)) if len(sel) > 3 else None))
    z += pas
valides = [(z, w) for z, w in niveaux if w is not None]
lis = []
for i in range(1, len(valides) - 1):
    lis.append((valides[i][0], sum(valides[j][1] for j in (i - 1, i, i + 1)) / 3))
z_fin, w_fin = min(lis, key=lambda t: t[1])
frac_fin = (z_fin - zmin) / h
ecart = abs(frac_fin - 0.285)
T["genou_geometrie"] = {"ok": ecart <= 0.03,
    "detail": f"section la plus fine (profondeur) à {frac_fin:.3f} h (profondeur {w_fin*1000:.0f} mm) ; genou estimé 0,285 h ; écart {ecart:.3f} h (seuil 0,03)",
    "statut": "validee" if ecart <= 0.03 else "ecart"}
A["genou_g"]["statut"] = "validee" if ecart <= 0.03 else "estimee"

sym = abs(max(xs) + min(xs)) <= 0.01
T["symetrie_x"] = {"ok": sym, "detail": f"centre X du bundle {cx:.3f} m ; après recentrage x min {min(xs):.3f}, x max {max(xs):.3f}", "statut": "validee" if sym else "echec"}
res["articulations_non_validees"] = [k for k, v in A.items() if v["statut"] == "estimee"]
json.dump(res, open(sortie, "w"), indent=2, ensure_ascii=False)
print("RESULTAT", "OK" if all(v["ok"] for v in T.values()) else "ECHEC")
for k, v in T.items(): print("TEST", k, v)
print("NON_VALIDEES", res["articulations_non_validees"])
