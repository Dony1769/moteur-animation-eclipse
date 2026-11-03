import bpy, sys, math, random, time, os

sortie = sys.argv[sys.argv.index("--") + 1]
t0 = time.time()
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
ASSETS = os.environ.get("ASSETS") or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "assets")
ph = os.path.join(ASSETS, "ph")

# 1. maillages téléchargés (Poly Haven, CC0) : chargés par nom exact, sans primitives
SOURCES = {
    "falaise": ("namaqualand_cliff_01", "namaqualand_cliff_01_LOD1"),
    "roc_a": ("rock_face_01", "rock_face_01"),
    "roc_b": ("rock_face_02", "rock_face_02"),
    "sable": ("sand_rocks_small_01", "sand_rocks_small_01_LOD3"),
}
gabarits = {}
for cle, (fichier, nom) in SOURCES.items():
    with bpy.data.libraries.load(f"{ph}/{fichier}.blend", link=False) as (src, dst):
        dst.objects = [nom]
    gabarits[cle] = bpy.data.objects[nom]
    print("CHARGE", cle, nom, len(gabarits[cle].data.vertices))

# textures Poly Haven : chemins absolus vers les cartes téléchargées
for im in bpy.data.images:
    if im.filepath.startswith("//textures/"):
        im.filepath = f"{ph}/textures/" + im.filepath.split("/")[-1]
        im.reload()

# les gabarits ne sont pas dans la scène : on les retire de la collection par défaut, on pose des instances liées
for g in gabarits.values():
    if g.name in sc.collection.objects:
        sc.collection.objects.unlink(g)

def instance(gabarit, nom, pos, rot_z, echelle):
    o = bpy.data.objects.new(nom, gabarit.data)       # données partagées : pas de copie du maillage
    o.location = pos
    o.rotation_euler = (0.0, 0.0, rot_z)
    o.scale = echelle
    sc.collection.objects.link(o)
    return o

rnd = random.Random(7)
# 2. parois : deux rangées de falaises et de rochers de part et d'autre d'un passage (axe Y)
for cote, x in (("G", -9.0), ("D", 9.0)):
    for i in range(-9, 10):
        y = i * 5.0 + rnd.uniform(-0.8, 0.8)
        gab = gabarits["falaise"] if i % 3 else gabarits["roc_a"]
        hauteur = rnd.uniform(3.0, 4.2)
        rot = (0.0 if cote == "G" else math.pi) + rnd.uniform(-0.3, 0.3)
        instance(gab, f"Paroi_{cote}{i}", (x + rnd.uniform(-1.0, 1.0), y, 0.0), rot,
                 (1.8, 1.8, hauteur * 2.2 / 4.6))

# 3. sable : débris et rochers au sol, en instances
for i in range(-6, 7):
    for j in range(-12, 13):
        x = i * 3.0
        y = j * 2.6
        instance(gabarits["sable"], f"Sable_{i}_{j}", (x, y, -0.05), rnd.choice((0.0, math.pi)),
                 (1.0, 1.0, 1.0))
print("DECOR", round(time.time() - t0, 1))

# 4. éclairage : HDRI de coucher de soleil (CC0, Poly Haven)
w = bpy.data.worlds.new("Monde"); w.use_nodes = True
nt = w.node_tree
env = nt.nodes.new("ShaderNodeTexEnvironment")
env.image = bpy.data.images.load(f"{ph}/belfast_sunset_puresky_1k.exr")
nt.links.new(env.outputs["Color"], nt.nodes["Background"].inputs["Color"])
sc.world = w
bg = nt.nodes["Background"]; bg.inputs["Strength"].default_value = 1.0
sc_film = True
# lumière dorée de fin de journée : soleil bas, teinte chaude (lampe seulement, pas de géométrie)
soleil_d = bpy.data.lights.new("Soleil", type="SUN")
soleil_d.energy = 6.0
soleil_d.color = (1.0, 0.72, 0.42)
soleil = bpy.data.objects.new("Soleil", soleil_d)
soleil.rotation_euler = (math.radians(68), 0.0, math.radians(35))
sc.collection.objects.link(soleil)

# 5. caméra : 35 mm, angle bas, profondeur de champ
cam_d = bpy.data.cameras.new("Cam")
cam_d.lens = 35
cam_d.dof.use_dof = True
cam_d.dof.focus_distance = 18.0
cam_d.dof.aperture_fstop = 2.8
cam = bpy.data.objects.new("Cam", cam_d)
cam.location = (0.0, -18.0, 1.6)
cam.rotation_euler = (math.radians(80), 0.0, 0.0)
sc.collection.objects.link(cam)
sc.camera = cam


# 5b. personnage Mixamo (placeholder) + animation de course (Running), boucle
M = os.path.join(ASSETS, "mixamo")
avant = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=f"{M}/Personnage_Maria.fbx", automatic_bone_orientation=True)
nouveaux = [o for o in bpy.data.objects if o not in avant]
arm_perso = [o for o in nouveaux if o.type == "ARMATURE"][0]
avant2 = set(bpy.data.objects)
bpy.ops.import_scene.fbx(filepath=f"{M}/Running.fbx", automatic_bone_orientation=True)
arm_course = [o for o in bpy.data.objects if o not in avant2 and o.type == "ARMATURE"][0]
action = arm_course.animation_data.action
arm_perso.animation_data_create()
arm_perso.animation_data.action = action
if action.slots: arm_perso.animation_data.action_slot = action.slots[0]
# l'action Mixamo est en quaternions : le mode de rotation doit être QUATERNION sinon rien ne s'applique
for pb in arm_perso.pose.bones:
    pb.rotation_mode = 'QUATERNION'
# course sur place : la translation horizontale du bassin (axes locaux X et Z, soit l'avance) est retirée,
# le rebond vertical (axe local Y) est conservé
for fc in list(action.fcurves):
    if fc.data_path == 'pose.bones["mixamorig:Hips"].location' and fc.array_index in (0, 2):
        action.fcurves.remove(fc)
for fc in action.fcurves:
    fc.modifiers.new("CYCLES")          # la course de 16 images tourne en boucle sur 96 images
for o in list(bpy.data.objects):
    if o not in nouveaux and o.type == "ARMATURE" and o is arm_course:
        bpy.data.objects.remove(o, do_unlink=True)
# hauteur mesurée en monde (bounding box du maillage au repos), puis mise à l'échelle de l'armature
from mathutils import Vector
sc.frame_set(1)
bpy.context.view_layer.update()
zs = [(o.matrix_world @ Vector(c)).z for o in nouveaux if o.type == "MESH" for c in o.bound_box]
hauteur = max(zs) - min(zs)
echelle = 1.75 / hauteur
arm_perso.scale = tuple(s * echelle for s in arm_perso.scale)
# le run Mixamo avance vers -Y ; on tourne de 180° pour qu'il coure vers +Y (loin de la caméra)
arm_perso.rotation_euler.z = math.pi
print("PERSO hauteur_monde", round(hauteur, 3), "echelle", round(echelle, 4), "action", action.name)
sc.frame_start, sc.frame_end = 1, 96
for o in nouveaux:
    if o.parent is None:
        o.location = (0.0, -9.0, 0.0)
sc.frame_set(int(os.environ.get('FRAME', '1')))

# 6. rendu : Cycles CPU, débruitage, 3 rebonds, sans caustiques, 1280x540
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU" if os.environ.get("DEVICE", "CPU") == "CPU" else "GPU"
if sc.cycles.device == "GPU":
    # essaie le backend demandé (OPTIX par défaut), puis CUDA ; n'active que les GPU, jamais le CPU
    prefs = bpy.context.preferences.addons["cycles"].preferences
    gpu = []
    for backend in (os.environ.get("BACKEND", "OPTIX"), "CUDA"):
        prefs.compute_device_type = backend
        prefs.get_devices()
        gpu = [d for d in prefs.devices if d.type != "CPU"]
        if gpu:
            break
    for d in prefs.devices:
        d.use = d.type != "CPU"
    sc.cycles.device = "GPU" if gpu else "CPU"
    print("RENDU", sc.cycles.device, prefs.compute_device_type if gpu else "-", [d.name for d in gpu])
sc.cycles.samples = int(os.environ.get("SPP", "16"))
sc.cycles.use_denoising = True
sc.cycles.denoiser = "OPENIMAGEDENOISE"
sc.cycles.max_bounces = 3
sc.cycles.caustics_reflective = False
sc.cycles.caustics_refractive = False
sc.render.resolution_x, sc.render.resolution_y = int(os.environ.get("RX", "1280")), int(os.environ.get("RY", "540"))
sc.render.film_transparent = False
sc.render.image_settings.file_format = "PNG"
sc.view_settings.view_transform = "AgX"
sc.render.filepath = f"{sortie}/chase_a_decor.png"
t1 = time.time()
bpy.ops.render.render(write_still=True)
print("TEMPS_RENDU_IMAGE", round(time.time() - t1, 1))
print("CHASE_A_DONE", round(time.time() - t0, 1))
