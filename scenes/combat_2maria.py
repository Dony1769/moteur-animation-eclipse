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



# 5b. deux Maria (même rig, textures différentes), animations en NLA, sept plans caméra liés aux marqueurs
import math as _m
from mathutils import Vector
NB = int(os.environ.get("NB", "1440"))          # 60 s à 24 i/s
M = os.path.join(ASSETS, "mixamo")

def charger(fichier):
    avant = set(bpy.data.objects)
    bpy.ops.import_scene.fbx(filepath=os.path.join(M, fichier), automatic_bone_orientation=True)
    return [o for o in bpy.data.objects if o not in avant]

def retirer_cubes(objs):
    # le FBX Mixamo contient un cube d'export : primitive visible, retirée
    for o in list(objs):
        if o.type == "MESH" and o.name.startswith("Cube"):
            bpy.data.objects.remove(o, do_unlink=True)

# animations : importées une fois, racine horizontale retirée (course et coups sur place)
ANIM = {}
for nom in ("Idle", "Sword_Slash", "Hit_Reaction"):
    nouveaux = charger(nom + ".fbx")
    arm_a = [o for o in nouveaux if o.type == "ARMATURE"][0]
    act = arm_a.animation_data.action
    act.use_fake_user = True
    for fc in list(act.fcurves):
        if fc.data_path == 'pose.bones["mixamorig:Hips"].location' and fc.array_index in (0, 2):
            act.fcurves.remove(fc)
    ANIM[nom] = act
    for o in nouveaux:
        bpy.data.objects.remove(o, do_unlink=True)

def teinter(mat, couleur):
    # texture conservée, teinte multipliée sur la couleur de base : variante de texture
    nt = mat.node_tree
    bsdf = [n for n in nt.nodes if n.type == "BSDF_PRINCIPLED"][0]
    entree = bsdf.inputs["Base Color"]
    lien = [l for l in nt.links if l.to_socket == entree]
    mix = nt.nodes.new("ShaderNodeMixRGB")
    mix.blend_type = "MULTIPLY"
    mix.inputs[0].default_value = 1.0
    mix.inputs[2].default_value = (couleur[0], couleur[1], couleur[2], 1.0)
    if lien:
        nt.links.new(lien[0].from_socket, mix.inputs[1])
        nt.links.remove(lien[0])
    else:
        mix.inputs[1].default_value = tuple(entree.default_value)
    nt.links.new(mix.outputs[0], entree)

PERSOS = {}
for cle, x, angle, teinte in (("A", -0.65, _m.pi / 2, None), ("B", 0.65, -_m.pi / 2, (0.35, 0.55, 1.0))):
    objs = charger("Personnage_Maria.fbx")
    retirer_cubes(objs)
    arm = [o for o in objs if o.type == "ARMATURE"][0]
    maillages = [o for o in objs if o.type == "MESH"]
    for pb in arm.pose.bones:
        pb.rotation_mode = "QUATERNION"
    if teinte:
        for m in maillages:
            for slot in m.material_slots:
                if slot.material:
                    slot.material = slot.material.copy()
                    teinter(slot.material, teinte)
    arm.rotation_euler.z = angle
    arm.location = (x, -9.0, 0.0)
    bpy.context.view_layer.update()
    zs = [(o.matrix_world @ Vector(c)).z for o in maillages for c in o.bound_box]
    echelle = 1.75 / (max(zs) - min(zs))
    arm.scale = tuple(s * echelle for s in arm.scale)
    PERSOS[cle] = arm
    print("PERSO", cle, round(echelle, 4))

# calendrier des coups : A attaque (Sword_Slash) ; B encaisse, puis contre-attaque
A_COUPS = [150, 330, 560, 760, 980, 1180, 1330]
B_COUPS = [470, 880, 1110, 1400]
def calendrier(cle):
    ev = []
    if cle == "A":
        ev += [(f, "Sword_Slash") for f in A_COUPS]
        ev += [(f + 12, "Hit_Reaction") for f in B_COUPS]
    else:
        ev += [(f, "Sword_Slash") for f in B_COUPS]
        ev += [(f + 12, "Hit_Reaction") for f in A_COUPS]
    return sorted(ev)

def poser_nla(arm, cle):
    ad = arm.animation_data_create()
    piste = ad.nla_tracks.new()
    curseur = 1
    def remplir_idle(jusqua):
        nonlocal curseur
        while curseur < jusqua:
            longueur = min(int(ANIM["Idle"].frame_range[1]), jusqua - curseur)
            s = piste.strips.new("Idle", curseur, ANIM["Idle"])
            s.action_frame_end = s.action_frame_start + longueur - 1
            curseur += longueur
    for debut, nom in calendrier(cle):
        if debut >= NB:
            continue
        remplir_idle(debut)
        act = ANIM[nom]
        longueur = int(act.frame_range[1] - act.frame_range[0]) + 1
        if debut < curseur:
            continue
        piste.strips.new(nom, debut, act)
        curseur = debut + longueur
    remplir_idle(NB + 1)

for cle, arm in PERSOS.items():
    poser_nla(arm, cle)

# caméras : sept plans, un par marqueur de timeline (caméra liée au marqueur)
RIG = bpy.data.objects.new("CamRig", None)
sc.collection.objects.link(RIG)
PLANS = [
    # (image, nom, position relative au rig, rotation X, Z en degrés, focale, distance de mise au point, ouverture)
    (1,    "PlanLarge",   (0.0, -14.0, 2.2), 84, 0,    35, 12.0, 2.8),
    (241,  "PlanMoyen",   (0.0, -12.5, 1.4), 90, 0,    35,  9.0, 2.8),
    (481,  "PlanProfilA", (-0.65, -11.6, 1.35), 90, 0, 50,  2.6, 2.0),
    (601,  "ContreJour",  (0.0, -12.0, 0.35), 96, 0,   35,  9.0, 2.8),
    (841,  "PlanProfilB", (0.65, -11.6, 1.35), 90, 0, 50,  2.6, 2.0),
    (1081, "PlanLarge2",  (0.0, -14.0, 3.0), 76, 0,    35, 12.0, 2.8),
    (1321, "PlanFinal",   (0.0, -12.5, 1.4), 90, 0,    35,  9.0, 2.8),
]
marqueurs = []
for frame, nom, pos, rot_x, rot_z, lentille, mise_au_point, ouverture in PLANS:
    c_d = bpy.data.cameras.new("Cam_" + nom)
    c_d.lens = lentille
    c_d.dof.use_dof = True
    c_d.dof.focus_distance = mise_au_point
    c_d.dof.aperture_fstop = ouverture
    c = bpy.data.objects.new("Cam_" + nom, c_d)
    sc.collection.objects.link(c)
    c.parent = RIG
    c.location = pos
    c.rotation_euler = (_m.radians(rot_x), 0.0, _m.radians(rot_z))
    m = sc.timeline_markers.new(nom, frame=frame)
    m.camera = c
    marqueurs.append(c)
sc.camera = marqueurs[0]

# secousse de caméra aux coups : l'empty parent des caméras
IMPACTS = sorted([f + 12 for f in A_COUPS] + [f + 12 for f in B_COUPS])
for f in range(1, NB + 1):
    k = 0.0
    for t in IMPACTS:
        if 0 <= f - t < 8:
            k += 0.05 * (1 - (f - t) / 8.0) * _m.sin((f - t) * 2.5)
    RIG.location = (k, 0.0, k * 0.5)
    RIG.keyframe_insert("location", frame=f)

sc.frame_start, sc.frame_end = int(os.environ.get("F0", "1")), int(os.environ.get("F1", str(NB)))
sc.frame_set(1)
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
sc.render.filepath = f"{sortie}/frame_"
t1 = time.time()
sc.render.use_motion_blur = True
sc.render.motion_blur_shutter = 0.5
bpy.ops.render.render(animation=True)
print("TEMPS_RENDU_IMAGE", round(time.time() - t1, 1))
print("COMBAT2_DONE", round(time.time() - t0, 1))
