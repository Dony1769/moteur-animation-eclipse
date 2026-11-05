"""Extraction des données de skinning pour le banc comparatif LBS / DQS / hybride (phase 4).

Une seule source pour les trois méthodes : même maillage de base, mêmes poids, même armature, mêmes matrices de pose.
Blender ne sert qu'à lire les données et à produire le contrôle (déformation évaluée par Blender) ; il ne déforme
rien pour les méthodes comparées.

Sorties (npz) :
  rest_monde (V,3) ; W_idx, W_w (V,K) poids bruts (indices d'os, -1 = vide) ; noms_os ; bones_rest_monde (J,4,4)
  pour chaque pose P : P__os (J,4,4) matrices de pose monde ; P__ctrl (V,3) positions évaluées par Blender (base)
  maillage haute résolution (MULTIRES niveau 3) : hr_rest (N,3), hr_boucle, hr_tot, b_boucle, b_tot ;
  pour quelques poses : P__hr (N,3) positions Blender sur le maillage haute résolution.
Tout est en mètres monde. Un JSON compagnon décrit les poses et les signes de flexion détectés.

Usage : blender -b --factory-startup --disable-autoexec ENTREE.blend -P engine/validation/skinning/extraire_poses.py -- ENTREE.blend SORTIE.npz
"""
import bpy
import sys
import json
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:]
entree, sortie = argv[0], argv[1]
OBJ = "GEO-body_male_realistic"

arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
src = bpy.data.objects[OBJ]
dg = bpy.context.evaluated_depsgraph_get

AW = np.array(arm.matrix_world, dtype=np.float64)
os_noms = [b.name for b in arm.data.bones]
idx = {n: i for i, n in enumerate(os_noms)}
J = len(os_noms)
bones_rest_arm = np.array([np.array(b.matrix_local, dtype=np.float64) for b in arm.data.bones])
bones_rest_monde = np.einsum("ij,njk->nik", AW, bones_rest_arm)


def positions_monde(obj, mesh):
    M = np.array(obj.matrix_world, dtype=np.float64)
    n = len(mesh.vertices)
    co = np.empty(n * 3, dtype=np.float64)
    mesh.vertices.foreach_get("co", co)
    co = co.reshape(n, 3)
    return co @ M[:3, :3].T + M[:3, 3]


def boucles(mesh):
    nl = len(mesh.loops)
    b = np.empty(nl, dtype=np.int64)
    mesh.loops.foreach_get("vertex_index", b)
    tot = np.empty(len(mesh.polygons), dtype=np.int64)
    mesh.polygons.foreach_get("loop_total", tot)
    return b, tot


def poser(angles):
    """angles : {nom d'os: (x, y, z) en radians, euler XYZ}. Retourne les matrices de pose en monde (J,4,4)."""
    for n in os_noms:
        pb = arm.pose.bones[n]
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0.0, 0.0, 0.0)
    for n, e in angles.items():
        arm.pose.bones[n].rotation_euler = e
    bpy.context.view_layer.update()
    return np.array([AW @ np.array(arm.pose.bones[n].matrix, dtype=np.float64) for n in os_noms])


def tete_monde(nom):
    return (AW @ np.array(arm.pose.bones[nom].matrix, dtype=np.float64))[:3, 3]


# -- maillage de base (sans MULTIRES) pour le contrôle et les poids --
copie = src.copy()
copie.data = src.data.copy()
copie.name = "BANC_base"
bpy.context.scene.collection.objects.link(copie)
for mo in list(copie.modifiers):
    if mo.type == "MULTIRES":
        copie.modifiers.remove(mo)
for mo in copie.modifiers:
    if mo.type == "ARMATURE":
        mo.object = arm

# -- poids bruts lus sur le maillage source --
noms_groupes = [g.name for g in src.vertex_groups]
V = len(src.data.vertices)
listes, ignores = [], 0
for v in src.data.vertices:
    items = []
    for g in v.groups:
        nom = noms_groupes[g.group]
        if nom in idx:
            if g.weight > 0:
                items.append((idx[nom], g.weight))
        else:
            ignores += 1
    items.sort(key=lambda t: -t[1])
    listes.append(items)
K = max(len(l) for l in listes)
W_idx = -np.ones((V, K), dtype=np.int64)
W_w = np.zeros((V, K), dtype=np.float64)
for i, l in enumerate(listes):
    for k, (j, w) in enumerate(l):
        W_idx[i, k] = j
        W_w[i, k] = w

# -- signes : détectés géométriquement, jamais supposés --
repos = poser({})
rest_knee_x = {}
signes = {}
for cote in ("Left", "Right"):
    haut, bas, pied = f"mixamorig:{cote}UpLeg", f"mixamorig:{cote}Leg", f"mixamorig:{cote}Foot"
    r_bas, r_pied = tete_monde(bas), tete_monde(pied)
    cote_x = np.sign(r_bas[0])

    def flex_ok(s):
        poser({haut: (s * np.radians(60), 0, 0)})
        return tete_monde(bas)[1] < r_bas[1] - 1e-3

    def genou_ok(s):
        poser({bas: (s * np.radians(60), 0, 0)})
        return tete_monde(pied)[1] > r_pied[1] + 1e-3

    def abd_ok(s):
        poser({haut: (0, 0, s * np.radians(30))})
        return (tete_monde(bas)[0] - r_bas[0]) * cote_x > 1e-3

    # La rotation autour de l'axe de la cuisse ne déplace pas un point situé sur cet axe. Le rig n'a pas d'os
    # d'orteil (19 os) : on mesure le bout de l'os du pied (tail), décalé vers l'avant.
    def bout_pied():
        pb = arm.pose.bones[pied]
        m = AW @ np.array(pb.matrix, dtype=np.float64)
        return (m @ np.array([0.0, pb.bone.length, 0.0, 1.0]))[:3]
    r_bout = bout_pied()

    def ext_ok(s):
        poser({haut: (0, s * np.radians(30), 0)})
        return (bout_pied()[0] - r_bout[0]) * cote_x > 1e-3

    def trouve(test, nom_test):
        for s in (1.0, -1.0):
            if test(s):
                return s
        raise SystemExit("BANC_ECHEC : signe introuvable pour " + cote + " (" + nom_test + ")")

    signes[cote] = {
        "flexion_hanche": trouve(flex_ok, "flexion"),
        "genou": trouve(genou_ok, "genou"),
        "abduction": trouve(abd_ok, "abduction"),
        "rotation_externe": trouve(ext_ok, "rotation"),
    }
poser({})

POSES = [
    ("flex30", dict(flex=30)), ("flex60", dict(flex=60)), ("flex90", dict(flex=90)), ("flex120", dict(flex=120)),
    ("abd30", dict(abd=30)), ("add20", dict(abd=-20)),
    ("ext30", dict(rot=30)), ("int30", dict(rot=-30)),
    ("genou30", dict(genou=30)), ("genou60", dict(genou=60)), ("genou90", dict(genou=90)),
    ("combo_flex90_abd30_ext30", dict(flex=90, abd=30, rot=30)),
    ("combo_flex120_genou90", dict(flex=120, genou=90)),
    ("combo_flex60_abd20_int20_genou60", dict(flex=60, abd=20, rot=-20, genou=60)),
]
HAUTE_RES_POSES = {"L_flex90", "L_flex120", "L_genou90", "L_combo_flex120_genou90", "R_flex90"}

data = {"rest_monde": positions_monde(copie, copie.data), "W_idx": W_idx, "W_w": W_w,
        "noms_os": np.array(os_noms), "bones_rest_monde": bones_rest_monde}
b_boucle, b_tot = boucles(copie.data)
data["b_boucle"], data["b_tot"] = b_boucle, b_tot

# maillage haute résolution au repos
src_ev = src.evaluated_get(dg()).data
data["hr_rest"] = positions_monde(src, src_ev).astype(np.float32)
h_boucle, h_tot = boucles(src_ev)
data["hr_boucle"], data["hr_tot"] = h_boucle, h_tot

meta = {"ignores_groupes_non_os": ignores, "signes": signes, "poses": {}}
for cote in ("L", "R"):
    cote_nom = "Left" if cote == "L" else "Right"
    s = signes[cote_nom]
    haut, bas = f"mixamorig:{cote_nom}UpLeg", f"mixamorig:{cote_nom}Leg"
    for nom, p in POSES:
        ang = {
            haut: (s["flexion_hanche"] * np.radians(p.get("flex", 0)),
                   s["rotation_externe"] * np.radians(p.get("rot", 0)),
                   s["abduction"] * np.radians(p.get("abd", 0))),
            bas: (s["genou"] * np.radians(p.get("genou", 0)), 0.0, 0.0),
        }
        nom_pose = f"{cote}_{nom}"
        P = poser(ang)
        data[nom_pose + "__os"] = P
        cev = copie.evaluated_get(dg()).data
        data[nom_pose + "__ctrl"] = positions_monde(copie, cev)
        if nom_pose in HAUTE_RES_POSES:
            sev = src.evaluated_get(dg()).data
            data[nom_pose + "__hr"] = positions_monde(src, sev).astype(np.float32)
        meta["poses"][nom_pose] = {"angles_deg": {k: [round(np.degrees(x), 3) for x in v] for k, v in ang.items()}}

poser({})
np.savez_compressed(sortie, **data)
with open(sortie.replace(".npz", ".json"), "w") as f:
    json.dump({"entree": entree, "objet": OBJ, "os": os_noms, "methode_controle": "Blender ARMATURE, maillage de base",
               **meta}, f, indent=2, ensure_ascii=False)
bpy.data.objects.remove(copie, do_unlink=True)
print("EXTRAIT_OK", sortie, "sommets", V, "poses", len(meta["poses"]), "signes", signes)
