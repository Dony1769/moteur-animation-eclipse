import bpy, math, os, sys
from mathutils import Vector
sc = bpy.context.scene
rig = bpy.data.objects["rig"]
bpy.context.view_layer.objects.active = rig
bpy.ops.object.mode_set(mode="POSE")
N = 16                       # un cycle complet = deux pas, 16 images à 24 i/s
# retire les contraintes des os de déformation : on les pose directement (méthode de l'ancien retargeting)
for pb in rig.pose.bones:
    if pb.name.startswith("DEF-"):
        for c in list(pb.constraints):
            pb.constraints.remove(c)
ANIME = ["DEF-thigh.L", "DEF-thigh.R", "DEF-shin.L", "DEF-shin.R", "DEF-upper_arm.L", "DEF-upper_arm.R",
         "DEF-forearm.L", "DEF-forearm.R", "DEF-foot.L", "DEF-foot.R", "DEF-spine.002", "DEF-spine"]
for nom in ANIME:
    pb = rig.pose.bones[nom]
    pb.rotation_mode = "XYZ"
    pb.rotation_euler = (0, 0, 0)
def pose(f):
    ph = 2 * math.pi * (f - 1) / N
    for cote, p in (("L", ph), ("R", ph + math.pi)):
        cuisse = -0.55 * math.sin(p)
        genou = -0.9 * max(0.0, math.sin(p + math.pi / 2))
        bras = 0.45 * math.sin(p + math.pi)
        avant_bras = 1.25 + 0.25 * math.sin(p)
        pied = -(cuisse + genou) * 0.9 + 0.15          # pied à plat pendant la foulée
        rig.pose.bones[f"DEF-thigh.{cote}"].rotation_euler = (cuisse, 0, 0)
        rig.pose.bones[f"DEF-shin.{cote}"].rotation_euler = (genou, 0, 0)
        rig.pose.bones[f"DEF-upper_arm.{cote}"].rotation_euler = (bras, 0, 0)
        rig.pose.bones[f"DEF-forearm.{cote}"].rotation_euler = (avant_bras, 0, 0)
        rig.pose.bones[f"DEF-foot.{cote}"].rotation_euler = (pied, 0, 0)
    rig.pose.bones["DEF-spine.002"].rotation_euler = (-0.12, 0, 0)
    rig.pose.bones["DEF-spine"].location = (0, 0, 0.03 * abs(math.cos(ph)))
    rig.pose.bones["DEF-spine"].keyframe_insert("location", frame=f)
    for nom in ANIME:
        rig.pose.bones[nom].keyframe_insert("rotation_euler", frame=f)
for f in range(1, N + 1):
    pose(f)
for fc in rig.animation_data.action.fcurves:
    fc.modifiers.new("CYCLES")
sc.frame_start, sc.frame_end = 1, N
bpy.ops.object.mode_set(mode="OBJECT")
# caméra de profil, fond blanc, lumière douce
cam = bpy.data.objects.new("Cam", bpy.data.cameras.new("Cam"))
sc.collection.objects.link(cam); sc.camera = cam
cam.data.lens = 50
cam.location = (3.6, 0.0, 1.0); cam.rotation_euler = (math.radians(90), 0, math.radians(90))
sun = bpy.data.objects.new("Sun", bpy.data.lights.new("Sun", "SUN")); sun.data.energy = 4
sc.collection.objects.link(sun); sun.rotation_euler = (math.radians(60), 0, math.radians(30))
w = bpy.data.worlds.new("W"); w.use_nodes = True
w.node_tree.nodes["Background"].inputs[0].default_value = (0.32, 0.34, 0.38, 1); sc.world = w
sc.render.engine = "CYCLES"; sc.cycles.device = "CPU"; sc.cycles.samples = 16
sc.cycles.use_denoising = True
sc.render.resolution_x, sc.render.resolution_y = 480, 540
sc.render.image_settings.file_format = "PNG"; sc.view_settings.view_transform = "Standard"
sortie = sys.argv[sys.argv.index("--") + 1]
os.makedirs(sortie, exist_ok=True)
for f in (1, 5, 9, 13):
    sc.frame_set(f)
    sc.render.filepath = f"{sortie}/guerrier_f{f:02d}.png"
    bpy.ops.render.render(write_still=True)
    print("IMG", f)
print("GUERRIER_DONE")
