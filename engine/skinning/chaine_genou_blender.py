"""Validation Blender de la chaîne de nœuds coaxiaux au genou (LBS réelle, pas numpy).

Construit dans une copie du maillage K+1 os de jonction coaxiaux (J0 au repos, Jk tourne de k·θ/K),
affecte les poids exportés (chaine_bl.npz), pose à θ et lit les sommets évalués par le modificateur Armature.

Usage : blender -b --factory-startup --disable-autoexec COPIE.blend -P engine/skinning/chaine_genou_blender.py -- CHAINE.npz SORTIE.npz ANGLES(60,90,...) K
"""
import sys, math, numpy as np, bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:]
chaine_npz, sortie, angles_s, K_s = argv[:4]
angles = [int(a) for a in angles_s.split(",")]
K = int(K_s)
D = np.load(chaine_npz, allow_pickle=True)
Wbl, pivot, rest = D["W"], D["pivot"], D["rest"]

corps = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
assert len(corps.data.vertices) == len(rest), f"{len(corps.data.vertices)} sommets, attendu {len(rest)}"
for mod in list(corps.modifiers):
    corps.modifiers.remove(mod)
for o in [o for o in bpy.data.objects if o.type == "ARMATURE"]:
    bpy.data.objects.remove(o, do_unlink=True)

arm_data = bpy.data.armatures.new("Chaine")
arm = bpy.data.objects.new("Chaine", arm_data)
bpy.context.collection.objects.link(arm)
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode="EDIT")
pv = Vector(pivot.tolist())
prev = None
for j in range(K + 1):
    eb = arm_data.edit_bones.new(f"J{j}")
    eb.head = pv; eb.tail = pv + Vector((0, 0, 0.05))
    if prev is not None:
        eb.parent = prev
    prev = eb
bpy.ops.object.mode_set(mode="OBJECT")

for g in list(corps.vertex_groups):
    corps.vertex_groups.remove(g)
groupes = [corps.vertex_groups.new(name=f"J{j}") for j in range(K + 1)]
for j in range(K + 1):
    idx = np.where(Wbl[:, j] > 0)[0].tolist()
    if idx:
        groupes[j].add(idx, 0.0, "REPLACE")
        for i in idx:
            groupes[j].add([i], float(Wbl[i, j]), "REPLACE")
mod = corps.modifiers.new("Armature", "ARMATURE")
mod.object = arm
mod.use_vertex_groups = True

cw, aw = corps.matrix_world.copy(), arm.matrix_world.copy()
inv_a = aw.inverted()
resultats = {}
for th in angles:
    bpy.context.view_layer.objects.active = arm
    bpy.ops.object.mode_set(mode="POSE")
    for j in range(K + 1):
        pb = arm.pose.bones[f"J{j}"]
        pb.rotation_mode = "XYZ"
        pb.rotation_euler = (0.0, 0.0, 0.0) if j == 0 else (math.radians(th) / K, 0.0, 0.0)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    dg = bpy.context.evaluated_depsgraph_get()
    ev = corps.evaluated_get(dg)
    pts = np.array([list(inv_a @ (cw @ v.co)) for v in ev.data.vertices])
    resultats[f"pts_{th}"] = pts
    print(f"θ={th} : sommets évalués {len(pts)}")

np.savez(sortie, **resultats)
print("écrit", sortie)
