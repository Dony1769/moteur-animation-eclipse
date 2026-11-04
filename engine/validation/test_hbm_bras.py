"""Phase 3 : bras, avant-bras et mains sur le corps HBM (sans armature d'origine).

Validations :
 - 8 os créés (épaule, bras, avant-bras, main, côtés G et D), aucun os de longueur nulle ;
 - longueurs dans les plages anatomiques (fractions de la hauteur) ;
 - symétrie gauche/droite des articulations (écart max en mm, seuil 15 mm) ;
 - milieu de chaque os à l'intérieur du maillage (parité des intersections, direction X extérieure) ;
 - bilan : quelles articulations sont mesurées, lesquelles sont extrapolées (rien n'est caché).
La source n'est pas modifiée (copie).
Usage : blender -b --factory-startup --disable-autoexec -P engine/validation/test_hbm_bras.py -- BUNDLE.blend SORTIE.json SCRATCH
"""
import bpy, sys, json, os, shutil
from mathutils import Vector, bvhtree, Matrix
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rigging"))
import bras_hbm
import doigts_hbm
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
bundle, sortie, scratch = argv[0], argv[1], argv[2]
os.makedirs(scratch, exist_ok=True)
copie = os.path.join(scratch, "bras_bundle.blend"); shutil.copy(bundle, copie)
bpy.ops.wm.open_mainfile(filepath=copie)
o = bpy.data.objects["GEO-body_male_realistic"]
P0 = [o.matrix_world @ v.co for v in o.data.vertices]
cx = (min(p.x for p in P0) + max(p.x for p in P0)) / 2
P = [Vector((p.x - cx, p.y, p.z)) for p in P0]
zmin = min(p.z for p in P); h = max(p.z for p in P) - zmin
pts_tuples = [(p.x, p.y, p.z) for p in P]

res = {"hauteur": round(h, 4), "joints": {}, "extrapole": {}, "tests": {}}
T = res["tests"]

chemins = {"G": bras_hbm.chemin_bras(pts_tuples, +1, zmin, h), "D": bras_hbm.chemin_bras(pts_tuples, -1, zmin, h)}
joints = {}
for cote, chem in chemins.items():
    pts, extra = bras_hbm.placer_articulations(chem, h)
    if pts is None:
        T["chemin_bras_" + cote] = {"ok": False, "detail": "chemin trop court"}
        continue
    joints[cote] = pts
    res["extrapole"][cote] = {k: v for k, v in extra.items() if v}
    res["joints"][cote] = {k: [round(c, 4) for c in v] for k, v in pts.items()}

# symétrie : miroir en X du côté gauche contre le côté droit
if len(joints) == 2:
    ecarts = []
    for k in ("epaule", "coude", "poignet", "bout_main"):
        g, d = joints["G"][k], joints["D"][k]
        ecarts.append(max(abs(abs(g[0]) - abs(d[0])), abs(g[1] - d[1]), abs(g[2] - d[2])))
    emax = max(ecarts)
    T["symetrie_bras"] = {"ok": emax <= 0.015, "detail": f"écart max {emax*1000:.1f} mm (seuil 15 mm)"}

# création de l'armature des bras (objet séparé, le maillage n'est pas modifié)
ad = bpy.data.armatures.new("HBM_Bras")
ao = bpy.data.objects.new("HBM_Bras", ad)
bpy.context.collection.objects.link(ao)
bpy.context.view_layer.objects.active = ao
bpy.ops.object.mode_set(mode="EDIT")
eb = {}
for cote, nom in (("G", "Left"), ("D", "Right")):
    if cote not in joints: continue
    j = joints[cote]
    V = lambda t: Vector(t)
    for n, (a, b) in {
        nom + "Arm": (j["epaule"], j["coude"]),
        nom + "ForeArm": (j["coude"], j["poignet"]),
        nom + "Hand": (j["poignet"], j["bout_main"]),
    }.items():
        e = ad.edit_bones.new(n); e.head = V(a); e.tail = V(b); e.use_connect = False
        eb[n] = e
    sh = ad.edit_bones.new(nom + "Shoulder"); sh.head = V(j["epaule"]); sh.tail = V(j["coude"]); sh.use_connect = False
    eb[nom + "Shoulder"] = sh
    eb[nom + "ForeArm"].parent = eb[nom + "Arm"]
    eb[nom + "Hand"].parent = eb[nom + "ForeArm"]
    eb[nom + "Arm"].parent = eb[nom + "Shoulder"]
# doigts : chaînes mesurées sur la main de chaque côté (rayon autour du poignet)
Pn = np.array([[p.x, p.y, p.z] for p in P])
doigts_par_cote = {}
for cote, nom in (("G", "Left"), ("D", "Right")):
    if cote not in joints: continue
    j = joints[cote]
    poignet = np.array(j["poignet"])
    bout = np.array(j["bout_main"])
    cote_mask = (Pn[:, 0] > 0.05) if cote == "G" else (Pn[:, 0] < -0.05)
    dist = np.linalg.norm(Pn - poignet, axis=1)
    main_pts = Pn[cote_mask & (dist < doigts_hbm.RAYON_MAIN)]
    res_d = doigts_hbm.doigts(main_pts, poignet, bout)
    doigts_par_cote[cote] = res_d
    for doig, f in res_d.items():
        parent = eb[nom + "Hand"]
        for k, (a, b) in enumerate(f["phalanges"]):
            e = ad.edit_bones.new(f"{nom}{doig.capitalize()}{k + 1}")
            e.head = Vector(a.tolist()); e.tail = Vector(b.tolist()); e.use_connect = False
            e.parent = parent
            parent = e
bpy.ops.object.mode_set(mode="OBJECT")

# longueurs et plages anatomiques
longs = {n: (b.tail_local - b.head_local).length for n, b in ad.bones.items()}
nul = [n for n, L in longs.items() if L < 0.01]
nb_bras = sum(1 for n in ad.bones.keys() if n.endswith(("Shoulder", "Arm", "ForeArm", "Hand")) and "Hand" not in n[-1:] and n[:4] in ("Left", "Righ") and not any(c.isdigit() for c in n))
nb_doigts = sum(1 for n in ad.bones.keys() if any(c.isdigit() for c in n))
T["os_bras_crees"] = {"ok": nb_bras == 8 and not nul, "detail": f"{nb_bras} os de bras (attendu 8), longueurs nulles {nul}"}
T["os_doigts_crees"] = {"ok": nb_doigts == 28, "detail": f"{nb_doigts} phalanges (attendu 28 : 2 pouce + 3x4 par main)"}
plages = {"Arm": (0.15, 0.22), "ForeArm": (0.12, 0.18), "Hand": (0.08, 0.13)}
hors = []
for n, L in longs.items():
    # correspondance sur le suffixe exact après le côté (Left/Right) : « LeftForeArm » ne doit pas tomber dans « Arm »
    cote_nom = n[4:] if n.startswith("Left") else n[5:]
    if cote_nom in plages:
        lo, hi = plages[cote_nom]
        if not (lo * h <= L <= hi * h):
            hors.append(f"{n}={L/h:.3f}h")
T["longueurs_anatomiques"] = {"ok": not hors, "detail": "hors plage : " + (", ".join(hors) or "aucun") +
                              " ; " + ", ".join(f"{n}={L:.3f} m" for n, L in longs.items() if n.startswith("Left"))}

# milieux des os à l'intérieur du maillage (même repère, BVH recentré)
bm = __import__("bmesh").new(); bm.from_mesh(o.data)
bm.transform(o.matrix_world)
bm.transform(Matrix.Translation((-cx, 0.0, 0.0)))
bvh = bvhtree.BVHTree.FromBMesh(bm)
def interieur(pt, d):
    n = 0; p = pt.copy()
    for _ in range(60):
        loc, nrm, idx, dist = bvh.ray_cast(p, d)
        if loc is None: break
        n += 1; p = loc + d * 1e-4
    return n % 2 == 1
dedans = {}
for n, b in ad.bones.items():
    if any(c.isdigit() for c in n): continue   # doigts : testés par test_hbm_doigts
    m = (b.head_local + b.tail_local) / 2
    d = Vector((1.0 if n.startswith("Left") else -1.0, 0, 0))
    dedans[n] = interieur(m, d)
hors_m = [n for n, v in dedans.items() if not v]
# doigts : même nombre et mêmes longueurs à gauche et à droite (écart max 10 mm), phalanges plausibles
if "G" in doigts_par_cote and "D" in doigts_par_cote:
    gg, dd = doigts_par_cote["G"], doigts_par_cote["D"]
    if set(gg) == set(dd):
        ecart = max(abs(gg[k]["longueur_m"] - dd[k]["longueur_m"]) for k in gg)
        T["symetrie_doigts"] = {"ok": ecart <= 0.010, "detail": f"{len(gg)} doigts de chaque côté ; écart max de longueur {ecart*1000:.1f} mm (seuil 10 mm)"}
    else:
        T["symetrie_doigts"] = {"ok": False, "detail": f"doigts différents : G={sorted(gg)} D={sorted(dd)}"}
phal = [len(f["phalanges"]) for c in doigts_par_cote.values() for f in c.values()]
bords = []
for c, dd_ in doigts_par_cote.items():
    for nom_d, f in dd_.items():
        for k, (a_, b_) in enumerate(f["phalanges"]):
            L_ = float(np.linalg.norm(np.array(b_) - np.array(a_)))
            if not (0.010 <= L_ <= 0.050):
                bords.append(f"{c}-{nom_d}{k+1}={L_*1000:.0f} mm")
T["phalanges_plausibles"] = {"ok": not bords, "detail": "hors plage 10-50 mm : " + (", ".join(bords) or "aucune")}
T["milieux_dans_maillage"] = {"ok": not hors_m, "detail": f"milieux hors du maillage : {hors_m or 'aucun'}"}
bm.free()

res["doigts"] = {c: {d: {"mesure": f["mesure"], "estime": f["estime"], "segments_estimes": f["segments_estimes"]} for d, f in dd.items()} for c, dd in doigts_par_cote.items()}
res["os"] = {n: {"tete": [round(c, 4) for c in b.head_local], "queue": [round(c, 4) for c in b.tail_local],
                  "parent": b.parent.name if b.parent else None} for n, b in ad.bones.items()}
json.dump(res, open(sortie, "w"), indent=2, ensure_ascii=False)
print("RESULTAT", "OK" if all(v["ok"] for v in T.values()) else "ECHEC " + ",".join(k for k, v in T.items() if not v["ok"]))
for k, v in T.items(): print("TEST", k, v)
