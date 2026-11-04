"""Test B, item 6 : création d'une armature pour le corps HBM sans skinning (tronc et jambes ; bras à venir).

Positions : chemins MESURÉS (centroïdes par tranche de hauteur) pour les jambes et le tronc, points
anatomiques en fraction de la hauteur pour les repères qui ne sont pas mesurés (voir docs).
Validations :
 - onze os créés, aucun os de longueur nulle, hiérarchie résolue ;
 - symétrie gauche/droite des chemins de jambe (à 1 cm près) ;
 - milieu de chaque os à l'intérieur du maillage (parité des intersections de rayons) ;
 - la source n'est pas modifiée (copie).
Usage : blender -b --factory-startup --disable-autoexec -P engine/validation/test_hbm_armature.py -- BUNDLE.blend SORTIE.json SCRATCH
"""
import bpy, sys, json, os, shutil
from mathutils import Vector, bvhtree

argv = sys.argv[sys.argv.index("--") + 1:]
bundle, sortie, scratch = argv[0], argv[1], argv[2]
os.makedirs(scratch, exist_ok=True)
copie = os.path.join(scratch, "bundle.blend"); shutil.copy(bundle, copie)
bpy.ops.wm.open_mainfile(filepath=copie)
o = bpy.data.objects[os.environ.get("HBM_OBJET", "GEO-body_male_realistic")]
P0 = [o.matrix_world @ v.co for v in o.data.vertices]
cx = (min(p.x for p in P0) + max(p.x for p in P0)) / 2
P = [Vector((p.x - cx, p.y, p.z)) for p in P0]
zmin = min(p.z for p in P); h = max(p.z for p in P) - zmin
res = {"hauteur": round(h, 4), "os": {}, "tests": {}}
T = res["tests"]

def fz(f): return zmin + f * h

def centre(zlo, zhi, cote):
    """Centroïde (x, y) des sommets d'une tranche de hauteur, côté +X (cote=+1) ou -X (cote=-1)."""
    # |x| < 0,25 : exclut les bras, qui descendent jusqu'à 0,46 h (erreur 43)
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
res["chemin_jambe_gauche"] = {str(k): [round(v[0], 4), round(v[1], 4)] for k, v in gauche.items()}
asym = max(abs(gauche[k][0] - droite[k][0]) + abs(gauche[k][1] - droite[k][1]) for k in gauche if k in droite)
T["symetrie_jambes"] = {"ok": asym <= 0.01, "detail": f"écart gauche/droite max {asym*1000:.1f} mm (seuil 10 mm)"}

# -- positions des os --
def pointe_pied(cote):
    """Pointe du pied mesurée : sommet le plus avancé en Y, près du sol, côté considéré (erreur 44 : pas de longueur fixe)."""
    sel = [p for p in P if p.z < zmin + 0.03 * h and cote * p.x > 0.03 and abs(p.x) < 0.25]
    return max(p.y for p in sel) if sel else 0.0

def jambe(cote, chem):
    hx, hy = chem[0.40]; kx, ky = chem[0.285]; ax, ay = chem[0.05]  # hanche : repère mesuré à 0,40 h, altitude 0,53 h (estimée)
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

# -- création de l'armature (nouvel objet, le maillage source n'est pas modifié) --
ad = bpy.data.armatures.new("HBM_Armature")
ao = bpy.data.objects.new("HBM_Armature", ad)
bpy.context.collection.objects.link(ao)
bpy.context.view_layer.objects.active = ao
bpy.ops.object.mode_set(mode="EDIT")
eb = {}
for nom, (a, b) in os_def.items():
    e = ad.edit_bones.new(nom); e.head = a; e.tail = b
    eb[nom] = e
for nom in ("LeftUpLeg", "RightUpLeg"): eb[nom].parent = eb["Hips"]
for nom in ("LeftLeg", "RightLeg"): eb[nom].parent = eb[nom.replace("Leg", "UpLeg")]
for nom in ("LeftFoot", "RightFoot"): eb[nom].parent = eb[nom.replace("Foot", "Leg")]
eb["Spine"].parent = eb["Hips"]; eb["Chest"].parent = eb["Spine"]
eb["Neck"].parent = eb["Chest"]; eb["Head"].parent = eb["Neck"]
for e in eb.values(): e.use_connect = False
bpy.ops.object.mode_set(mode="OBJECT")

# -- validations --
longs = [(n, round((b.tail_local - b.head_local).length, 4)) for n, b in ad.bones.items()]
nul = [n for n, L in longs if L < 0.01]
T["11_os_crees"] = {"ok": len(ad.bones) == 11 and not nul, "detail": f"{len(ad.bones)} os, longueurs nulles {nul}"}
racines = [b.name for b in ad.bones if b.parent is None]
T["hierarchie"] = {"ok": racines == ["Hips"], "detail": f"racine(s) {racines}"}

bm = __import__("bmesh").new(); bm.from_mesh(o.data)
bm.transform(o.matrix_world)
# même repère que les os : recentrage en X (erreur 41 : le BVH doit être dans le repère des os)
bm.transform(__import__("mathutils").Matrix.Translation((-cx, 0.0, 0.0)))
bvh = bvhtree.BVHTree.FromBMesh(bm)
def interieur(pt):
    """Parité des intersections dans la direction vers l'extérieur du membre (X), sinon vers le haut.
    Vers le haut, la cuisse traverse le bassin, dont les pièces se recouvrent : la parité y est fausse (erreur 42)."""
    d = Vector((1.0 if pt.x > 0.02 else -1.0, 0, 0)) if abs(pt.x) > 0.02 else Vector((0, 0, 1))
    n = 0; p = pt.copy()
    for _ in range(50):
        loc, nrm, idx, dist = bvh.ray_cast(p, d)
        if loc is None: break
        n += 1; p = loc + d * 1e-4
    return n % 2 == 1
dedans = {}
for n, b in ad.bones.items():
    m = (b.head_local + b.tail_local) / 2
    dedans[n] = interieur(m)
hors = [n for n, v in dedans.items() if not v]
T["milieux_dans_maillage"] = {"ok": not hors, "detail": f"milieux hors du maillage : {hors}"}
bm.free()
res["os"] = {n: {"tete": [round(v, 4) for v in b.head_local], "queue": [round(v, 4) for v in b.tail_local], "parent": b.parent.name if b.parent else None} for n, b in ad.bones.items()}
res["arms_non_crees"] = "bras non créés : coude et poignet non validés (erreur 40)"
json.dump(res, open(sortie, "w"), indent=2, ensure_ascii=False)
print("RESULTAT", "OK" if all(v["ok"] for v in T.values()) else "ECHEC " + ",".join(k for k, v in T.items() if not v["ok"]))
for k, v in T.items(): print("TEST", k, v)
