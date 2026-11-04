"""Phase 3 : squelette complet du corps HBM, une seule armature (sans skinning).

Os : jambes et tronc (11, comme test_hbm_armature), bras (8 : épaule, bras, avant-bras, main, G et D),
doigts (28 : pouce 2 phalanges, autres doigts 3, G et D).
Validations :
 - 47 os, aucun os de longueur nulle, racine unique Hips ;
 - symétrie G/D : jambes (10 mm), bras (15 mm), doigts (10 mm sur la longueur) ;
 - milieux des os de tronc, jambes et bras à l'intérieur du maillage (parité, direction X ou Z) ;
 - phalanges mesurées dans le maillage (épaisseur, deux sens) ; estimées : non testées, nommées ;
 - bilan explicite mesuré / estimé pour chaque os.
Fichier de sortie : le squelette est enregistré dans SCRATCH/HBM_squelette_complet.blend (le corps source n'est pas modifié).
Usage : blender -b --factory-startup --disable-autoexec -P engine/validation/test_hbm_complet.py -- BUNDLE.blend SORTIE.json SCRATCH
"""
import bpy, sys, json, os, shutil
import numpy as np
from mathutils import Vector, Matrix, bvhtree
import bmesh
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "rigging"))
import bras_hbm, doigts_hbm

argv = sys.argv[sys.argv.index("--") + 1:]
bundle, sortie, scratch = argv[0], argv[1], argv[2]
os.makedirs(scratch, exist_ok=True)
copie = os.path.join(scratch, "complet_bundle.blend"); shutil.copy(bundle, copie)
bpy.ops.wm.open_mainfile(filepath=copie)
o = bpy.data.objects["GEO-body_male_realistic"]
P0 = [o.matrix_world @ v.co for v in o.data.vertices]
cx = (min(p.x for p in P0) + max(p.x for p in P0)) / 2
P = [Vector((p.x - cx, p.y, p.z)) for p in P0]
zmin = min(p.z for p in P); h = max(p.z for p in P) - zmin
Pn = np.array([[p.x, p.y, p.z] for p in P])
def fz(f): return zmin + f * h

T, mesure, estime = {}, {}, {}

# ---------- jambes et tronc (même méthode que test_hbm_armature) ----------
def centre(zlo, zhi, cote):
    sel = [p for p in P if zlo <= p.z <= zhi and cote * p.x > 0.03 and abs(p.x) < 0.25]
    if len(sel) < 4: return None
    return (sum(abs(p.x) for p in sel) / len(sel), sum(p.y for p in sel) / len(sel))
def chemin_jambe(cote):
    pts = {}
    for f in (0.05, 0.10, 0.20, 0.285, 0.36, 0.40):
        c = centre(fz(f) - 0.01 * h, fz(f) + 0.01 * h, cote)
        if c: pts[f] = c
    return pts
gauche = chemin_jambe(+1); droite = chemin_jambe(-1)
asym = max(abs(gauche[k][0] - droite[k][0]) + abs(gauche[k][1] - droite[k][1]) for k in gauche if k in droite)
T["symetrie_jambes"] = {"ok": asym <= 0.01, "detail": f"écart max {asym*1000:.1f} mm (seuil 10 mm)"}
def pointe_pied(cote):
    sel = [p for p in P if p.z < zmin + 0.03 * h and cote * p.x > 0.03 and abs(p.x) < 0.25]
    return max(p.y for p in sel) if sel else 0.0
def jambe(cote, chem):
    hx, hy = chem[0.40]; kx, ky = chem[0.285]; ax, ay = chem[0.05]
    return {
        "UpLeg": (Vector((cote * hx, hy, fz(0.53))), Vector((cote * kx, ky, fz(0.285)))),
        "Leg": (Vector((cote * kx, ky, fz(0.285))), Vector((cote * ax, ay, fz(0.04)))),
        "Foot": (Vector((cote * ax, ay, fz(0.04))), Vector((cote * ax, pointe_pied(cote), fz(0.01)))),
    }
cy = sum(p.y for p in P) / len(P)
os_def = {}
for nom, cote, chem in (("Left", +1, gauche), ("Right", -1, droite)):
    for k, v in jambe(cote, chem).items():
        os_def[nom + k] = v
os_def["Hips"] = (Vector((0, cy, fz(0.53))), Vector((0, cy, fz(0.60))))
os_def["Spine"] = (Vector((0, cy, fz(0.60))), Vector((0, cy, fz(0.70))))
os_def["Chest"] = (Vector((0, cy, fz(0.70))), Vector((0, cy, fz(0.82))))
os_def["Neck"] = (Vector((0, cy, fz(0.82))), Vector((0, cy, fz(0.87))))
os_def["Head"] = (Vector((0, cy, fz(0.87))), Vector((0, cy, fz(1.0))))
for n in os_def: mesure[n] = "chemin mesuré (jambes/tronc)" if n != "Hips" else "hanche estimée à 0,53 h"

# ---------- bras (même méthode que test_hbm_bras) ----------
pts_tuples = [(p.x, p.y, p.z) for p in P]
joints = {}
for cote, nom in (("G", "Left"), ("D", "Right")):
    chem = bras_hbm.chemin_bras(pts_tuples, +1 if cote == "G" else -1, zmin, h)
    pts, extra = bras_hbm.placer_articulations(chem, h)
    joints[cote] = pts
    for k, v in extra.items():
        if v: estime[f"{nom}:{k}"] = "extrapolé/estimé (bras)"
    seg = {"Shoulder": (pts["epaule"], pts["coude"]), "Arm": (pts["epaule"], pts["coude"]),
           "ForeArm": (pts["coude"], pts["poignet"]), "Hand": (pts["poignet"], pts["bout_main"])}
    for k, (a_, b_) in seg.items():
        os_def[nom + k] = (Vector(a_), Vector(b_))
    mesure[nom + "Arm"] = mesure[nom + "ForeArm"] = mesure[nom + "Hand"] = "chemin mesuré, coude estimé"
    os_def[nom + "Shoulder"] = (Vector(pts["epaule"]), Vector(pts["coude"]))
    mesure[nom + "Shoulder"] = "chemin mesuré"

# ---------- doigts (même méthode que test_hbm_doigts) ----------
doigts_par_cote = {}
dfinger_defs = {}
for cote, nom in (("G", "Left"), ("D", "Right")):
    j = joints[cote]
    poignet = np.array(j["poignet"]); bout = np.array(j["bout_main"])
    cote_mask = (Pn[:, 0] > 0.05) if cote == "G" else (Pn[:, 0] < -0.05)
    dist = np.linalg.norm(Pn - poignet, axis=1)
    main_pts = Pn[cote_mask & (dist < doigts_hbm.RAYON_MAIN)]
    res_d = doigts_hbm.doigts(main_pts, poignet, bout)
    doigts_par_cote[cote] = res_d
    for doig, f in res_d.items():
        parent_nom = nom + "Hand"
        for k, (a_, b_) in enumerate(f["phalanges"]):
            nm = f"{nom}{doig.capitalize()}{k + 1}"
            dfinger_defs[nm] = (a_, b_, parent_nom, k in f["segments_estimes"])
            parent_nom = nm

# ---------- construction d'une seule armature ----------
ad = bpy.data.armatures.new("HBM_Squelette")
ao = bpy.data.objects.new("HBM_Squelette", ad)
bpy.context.collection.objects.link(ao)
bpy.context.view_layer.objects.active = ao
bpy.ops.object.mode_set(mode="EDIT")
eb = {}
for nom, (a_, b_) in os_def.items():
    e = ad.edit_bones.new(nom); e.head = a_; e.tail = b_; e.use_connect = False
    eb[nom] = e
for nm, (a_, b_, _, _) in dfinger_defs.items():
    e = ad.edit_bones.new(nm); e.head = Vector(a_.tolist()); e.tail = Vector(b_.tolist()); e.use_connect = False
    eb[nm] = e
# hiérarchie : Hips racine ; jambes et tronc comme test_hbm_armature ; épaules sous Chest
for nom in ("LeftUpLeg", "RightUpLeg"): eb[nom].parent = eb["Hips"]
for nom in ("LeftLeg", "RightLeg"): eb[nom].parent = eb[nom.replace("Leg", "UpLeg")]
for nom in ("LeftFoot", "RightFoot"): eb[nom].parent = eb[nom.replace("Foot", "Leg")]
eb["Spine"].parent = eb["Hips"]; eb["Chest"].parent = eb["Spine"]
eb["Neck"].parent = eb["Chest"]; eb["Head"].parent = eb["Neck"]
for nom in ("LeftShoulder", "RightShoulder"): eb[nom].parent = eb["Chest"]
for nom in ("Left", "Right"):
    eb[nom + "Arm"].parent = eb[nom + "Shoulder"]
    eb[nom + "ForeArm"].parent = eb[nom + "Arm"]
    eb[nom + "Hand"].parent = eb[nom + "ForeArm"]
for nm, (_, _, parent_nom, _) in dfinger_defs.items():
    eb[nm].parent = eb[parent_nom]
bpy.ops.object.mode_set(mode="OBJECT")

# ---------- validations ----------
nb = len(ad.bones)
longs = {n: (b.tail_local - b.head_local).length for n, b in ad.bones.items()}
nul = [n for n, L in longs.items() if L < 0.01]
T["47_os"] = {"ok": nb == 47 and not nul, "detail": f"{nb} os (attendu 47), longueurs nulles {nul or 'aucune'}"}
racines = [b.name for b in ad.bones if b.parent is None]
T["racine_unique"] = {"ok": racines == ["Hips"], "detail": f"racines {racines}"}

# symétrie bras et doigts
ecart_bras = max(max(abs(abs(joints["G"][k][0]) - abs(joints["D"][k][0])), abs(joints["G"][k][1] - joints["D"][k][1]), abs(joints["G"][k][2] - joints["D"][k][2])) for k in ("epaule", "coude", "poignet", "bout_main"))
T["symetrie_bras"] = {"ok": ecart_bras <= 0.015, "detail": f"écart max {ecart_bras*1000:.1f} mm (seuil 15 mm)"}
gg, dd = doigts_par_cote["G"], doigts_par_cote["D"]
if set(gg) == set(dd):
    ec = max(abs(gg[k]["longueur_m"] - dd[k]["longueur_m"]) for k in gg)
    T["symetrie_doigts"] = {"ok": ec <= 0.010, "detail": f"{len(gg)} doigts par côté ; écart de longueur max {ec*1000:.1f} mm"}
else:
    T["symetrie_doigts"] = {"ok": False, "detail": f"doigts différents G={sorted(gg)} D={sorted(dd)}"}

# milieux des os de corps à l'intérieur du maillage (parité, direction X ou Z : même règle que test_hbm_armature)
bm = bmesh.new(); bm.from_mesh(o.data); bm.transform(o.matrix_world)
bm.transform(Matrix.Translation((-cx, 0.0, 0.0)))
bvh = bvhtree.BVHTree.FromBMesh(bm)
def interieur(pt):
    d = Vector((1.0 if pt.x > 0.02 else -1.0, 0, 0)) if abs(pt.x) > 0.02 else Vector((0, 0, 1))
    n = 0; p = pt.copy()
    for _ in range(50):
        loc, nrm, idx, dist = bvh.ray_cast(p, d)
        if loc is None: break
        n += 1; p = loc + d * 1e-4
    return n % 2 == 1
hors = []
for n, b in ad.bones.items():
    if n in dfinger_defs: continue
    m = (b.head_local + b.tail_local) / 2
    if not interieur(m): hors.append(n)
T["milieux_corps_dans_maillage"] = {"ok": not hors, "detail": f"hors du maillage : {hors or 'aucun'}"}

# phalanges mesurées : dans l'épaisseur de la main, deux sens ; estimées : non testées
_, _, nmain = doigts_hbm.repere(Pn[(np.linalg.norm(Pn - np.array(joints["G"]["poignet"]), axis=1) < doigts_hbm.RAYON_MAIN) & (Pn[:, 0] > 0.05)], np.array(joints["G"]["poignet"]), np.array(joints["G"]["bout_main"]))
dehors, verif, non_t = [], 0, []
for nm, (a_, b_, _, estime_seg) in dfinger_defs.items():
    if estime_seg:
        non_t.append(nm); continue
    verif += 1
    m = Vector(((np.array(a_) + np.array(b_)) / 2).tolist())
    # même test que test_hbm_doigts : parité dans les deux sens de l'épaisseur de la main
    cnt_p = 0; p_ = m.copy()
    for _ in range(50):
        loc, nrm, idx, dist = bvh.ray_cast(p_, Vector(nmain.tolist()))
        if loc is None: break
        cnt_p += 1; p_ = loc + Vector(nmain.tolist()) * 1e-4
    cnt_m = 0; p_ = m.copy()
    for _ in range(50):
        loc, nrm, idx, dist = bvh.ray_cast(p_, Vector((-nmain).tolist()))
        if loc is None: break
        cnt_m += 1; p_ = loc + Vector((-nmain).tolist()) * 1e-4
    if not (cnt_p % 2 == 1 and cnt_m % 2 == 1):
        dehors.append(nm)
T["phalanges_mesurees_dans_maillage"] = {"ok": not dehors and verif > 0,
    "detail": f"{verif} phalanges mesurées testées ; hors : {dehors or 'aucune'} ; non testées (estimées) : {non_t}"}
bm.free()

# bilan explicite
T["bilan_mesure_estime"] = {"ok": True, "detail": json.dumps({"estime_bras_doigts": list(estime.keys()) + non_t}, ensure_ascii=False)}

# enregistrement du squelette complet (fichier de travail, le corps source n'est pas modifié)
sauve = os.path.join(scratch, "HBM_squelette_complet.blend")
bpy.ops.wm.save_as_mainfile(filepath=sauve, copy=True)
res = {"hauteur": round(h, 4), "nombre_os": nb, "fichier": sauve,
       "os": {n: {"tete": [round(v, 4) for v in b.head_local], "queue": [round(v, 4) for v in b.tail_local],
                   "parent": b.parent.name if b.parent else None, "mesure": mesure.get(n, "doigt : voir test_hbm_doigts") if n not in dfinger_defs else ("estime" if dfinger_defs[n][3] else "mesure")}
              for n, b in ad.bones.items()},
       "tests": T}
json.dump(res, open(sortie, "w"), indent=2, ensure_ascii=False)
print("RESULTAT", "OK" if all(v["ok"] for v in T.values()) else "ECHEC " + ",".join(k for k, v in T.items() if not v["ok"]))
for k, v in T.items(): print("TEST", k, v)
