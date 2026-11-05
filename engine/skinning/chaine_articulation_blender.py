"""Validation Blender générique d'une articulation en charnière par chaîne de nœuds coaxiaux (LBS réelle).

Entrée CHAINE.npz : W (N,K+1), pivot (3,), axe (3,) dans le repère armature, angles (en degrés).
Construit K+1 os J0..JK (J0 au repos), chaque Jk (k≥1) tourne de θ/K autour de l'axe (repère local de l'os),
lit les sommets évalués par le modificateur Armature, et écrit SORTIE.npz (pts_θ).
Usage : blender -b --factory-startup --disable-autoexec COPIE.blend -P ... -- CHAINE.npz SORTIE.npz ANGLES K
"""
import sys, math, numpy as np, bpy
from mathutils import Vector, Matrix

argv = sys.argv[sys.argv.index("--") + 1:]
chaine_npz, sortie, angles_s, K_s = argv[:4]
angles = [int(a) for a in angles_s.split(",")]
K = int(K_s)
D = np.load(chaine_npz, allow_pickle=True)
Wc, pivot, axe, rest = D["W"], D["pivot"], D["axe"], D["rest"]

corps = max([o for o in bpy.data.objects if o.type == "MESH"], key=lambda o: len(o.data.vertices))
assert len(corps.data.vertices) == len(rest), f"{len(corps.data.vertices)} sommets, attendu {len(rest)}"
for mod in list(corps.modifiers):
    corps.modifiers.remove(mod)
for o in [o for o in bpy.data.objects if o.type == "ARMATURE"]:
    bpy.data.objects.remove(o, do_unlink=True)

arm_data = bpy.data.armatures.new("Articulation")
arm = bpy.data.objects.new("Articulation", arm_data)
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
# axe dans le repère local de chaque os (orientation de repos identique pour tous les J)
rot_rest = arm_data.bones["J1"].matrix_local.to_3x3()
axe_local = rot_rest.inverted() @ Vector(axe.tolist())

for g in list(corps.vertex_groups):
    corps.vertex_groups.remove(g)
groupes = [corps.vertex_groups.new(name=f"J{j}") for j in range(K + 1)]
for j in range(K + 1):
    for i in np.where(Wc[:, j] > 0)[0].tolist():
        groupes[j].add([i], float(Wc[i, j]), "REPLACE")
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
        pb.rotation_mode = "AXIS_ANGLE"
        ang = 0.0 if j == 0 else math.radians(th) / K
        pb.rotation_axis_angle = (ang, axe_local.x, axe_local.y, axe_local.z)
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.update()
    ev = corps.evaluated_get(bpy.context.evaluated_depsgraph_get())
    resultats[f"pts_{th}"] = np.array([list(inv_a @ (cw @ v.co)) for v in ev.data.vertices])
    print(f"θ={th} sommets {len(ev.data.vertices)}")
np.savez(sortie, **resultats)
print("écrit", sortie)
