"""Attribution de l étirement de la hanche (phase 4) : à 120 degrés de flexion de la cuisse gauche, quels sommets
sont étirés (arête > 1,15), quels os les pilotent et à quelle hauteur. Banc LBS, maillage de base, mètres monde.
Usage : blender -b --factory-startup --disable-autoexec CORPS_SKIN.blend -P engine/validation/attribution_hanche.py
"""
import bpy, math, collections, sys
from mathutils import Euler
arm = next(o for o in bpy.data.objects if o.type == "ARMATURE")
src = bpy.data.objects["GEO-body_male_realistic"]
c = src.copy(); c.data = src.data.copy(); bpy.context.scene.collection.objects.link(c)
for mo in list(c.modifiers):
    if mo.type == "MULTIRES": c.modifiers.remove(mo)
for mo in c.modifiers:
    if mo.type == "ARMATURE": mo.object = arm
pb = arm.pose.bones["mixamorig:LeftUpLeg"]; pb.rotation_mode = "XYZ"
def pos():
    bpy.context.view_layer.update()
    ev = c.evaluated_get(bpy.context.evaluated_depsgraph_get()).data
    return [c.matrix_world @ v.co for v in ev.vertices], [tuple(p.vertices) for p in ev.polygons]
pb.rotation_euler = Euler((0,0,0),"XYZ"); R, polys = pos()
aretes = {}
for p in polys:
    for i in range(len(p)):
        a, b = sorted((p[i], p[(i+1)%len(p)])); aretes[(a,b)] = 1
pb.rotation_euler = Euler((math.radians(120)*-1.0,0,0),"XYZ"); P, _ = pos()
ratio_v = collections.defaultdict(float)
for a,b in aretes:
    l0 = (R[a]-R[b]).length
    if l0 < 1e-9: continue
    r = (P[a]-P[b]).length / l0
    if r > 1.15:
        ratio_v[a] = max(ratio_v[a], r); ratio_v[b] = max(ratio_v[b], r)
names = [g.name for g in c.vertex_groups]
bones = collections.Counter(); zs = []
for vi in ratio_v:
    v = c.data.vertices[vi]
    best = max(v.groups, key=lambda g: g.weight) if v.groups else None
    bones[names[best.group] + ("" if best.weight > 0.5 else "(<0.5)")] += 1
    zs.append(R[vi].z)
print("ATTRIB sommets_etires", len(ratio_v), "sur", len(R))
print("ATTRIB os_dominant", bones.most_common(8))
if zs: print("ATTRIB z_repos min/med/max", round(min(zs),3), round(sorted(zs)[len(zs)//2],3), round(max(zs),3))
print("ATTRIB hanche_LeftUpLeg_tete_z", round(arm.matrix_world.translation.z + 0,3))
