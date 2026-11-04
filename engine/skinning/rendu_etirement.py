import bpy, sys
from mathutils import Vector
sys.path.insert(0, "/home/claude/moteur_3_0/engine/skinning")
import pose_chaine as pc
S = "/tmp/claude-0/-home-claude/9ce8e1e5-f7cf-5619-8a75-3c6d9a11ab1c/scratchpad"
argv = sys.argv[sys.argv.index("--") + 1:]
ANGLE = float(argv[0]); SORTIE = argv[1]
bpy.ops.wm.open_mainfile(filepath=S + "/corps_final.blend")
corps = bpy.data.objects["GEO-body_male_realistic"]
arm = [m.object for m in corps.modifiers if m.type == "ARMATURE"][0]
corps.modifiers["Multires"].show_viewport = False
kb = corps.data.shape_keys.key_blocks
for k in kb: k.value = 0.0
v1 = min(ANGLE / 90, 1.0); v2 = max(0.0, min((ANGLE - 90) / 30, 1.0))
kb["corr_LeftArm"].value = v1; kb["c120_LeftArm"].value = v2
bpy.context.view_layer.update()
sauve = pc.poser_chaine(arm, [("mixamorig:LeftArm", (0, 1, 0), ANGLE)])
dg = bpy.context.evaluated_depsgraph_get()
ev = corps.evaluated_get(dg); m = ev.to_mesh()
pos = [v.co.copy() for v in m.vertices]
# repos : base avec clés à 0
for k in kb: k.value = 0.0
bpy.context.view_layer.update()
dg = bpy.context.evaluated_depsgraph_get(); ev0 = corps.evaluated_get(dg); m0 = ev0.to_mesh()
rest = [v.co.copy() for v in m0.vertices]
ev0.to_mesh_clear()
n = len(pos); pire = [1.0] * n
for e in corps.data.edges:
    a, b = e.vertices
    lr = (rest[a] - rest[b]).length
    if lr <= 0: continue
    r = (pos[a] - pos[b]).length / lr
    dev = max(r, 1.0 / r) if r > 0 else 99.0
    pire[a] = max(pire[a], dev); pire[b] = max(pire[b], dev)
# recoloration : vert (1) -> rouge (>=3)
col = corps.data.color_attributes.new(name="etirement", type="FLOAT_COLOR", domain="POINT")
for i, p in enumerate(pire):
    t = min(max((p - 1.0) / 2.0, 0.0), 1.0)
    col.data[i].color = (t, 1.0 - t, 0.1, 1.0)
corps.data.color_attributes.active_color = col
# caméra et rendu
for o in list(bpy.data.objects):
    if o.type == "CAMERA": bpy.data.objects.remove(o)
cam_d = bpy.data.cameras.new("cam"); cam = bpy.data.objects.new("cam", cam_d)
bpy.context.scene.collection.objects.link(cam)
from mathutils import Vector as V
W=[corps.matrix_world @ v for v in pos]; xs=[v.x for v in W]; ys=[v.y for v in W]; zs=[v.z for v in W]
cx=(max(xs)+min(xs))/2; cy=(max(ys)+min(ys))/2; cz=(max(zs)+min(zs))/2
cible = V((cx, cy, cz))
cam.location = V((cx + 4.2, cy, cz))
print("CENTRE", cx, cy, cz, "matrix", corps.matrix_world.translation)
cam.rotation_euler = (cible - cam.location).to_track_quat("-Z", "Y").to_euler()
cam_d.lens = 50
sc = bpy.context.scene
sc.camera = cam
sc.render.engine = "BLENDER_WORKBENCH"
sc.render.resolution_x = 900; sc.render.resolution_y = 900
sc.display.shading.light = "FLAT"
sc.display.shading.color_type = "VERTEX"
sc.render.filepath = SORTIE
kb["corr_LeftArm"].value = v1; kb["c120_LeftArm"].value = v2
bpy.context.view_layer.update()
bpy.ops.render.render(write_still=True)
print("OK", SORTIE, "max deviation", round(max(pire), 2))
